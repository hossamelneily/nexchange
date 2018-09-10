# -*- coding: utf-8 -*-


from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from nexchange.utils import get_client_ip
from core.models import Currency
from orders.models import Order
from payments.models import Payment, PaymentPreference, PaymentMethod,\
    PushRequest
from payments.utils import get_sha256_sign
from payments.task_summary import set_preference_for_verifications_invoke, \
    set_preference_bank_bin_invoke
from decimal import Decimal
from django.views.generic import View
from django.utils.decorators import method_decorator
from datetime import datetime
from nexchange.utils import ip_in_iplist
from risk_management.task_summary import order_cover_invoke


class SafeChargeListenView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SafeChargeListenView, self).dispatch(request,
                                                          *args, **kwargs)

    def get_or_create_payment_preference(self, unique_cc, name_on_card,
                                         product_id, payment_method,
                                         push_request=None):
        unknown_msg = 'method_{}_order_{}'.format(
            payment_method,
            product_id
        ) if product_id else ''
        _payment_method = PaymentMethod.objects.get(
            name__icontains='Safe Charge')
        pref_args = {
            'provider_system_id': unique_cc,
            'payment_method': _payment_method
        }
        if unique_cc:
            payment_pref_list = PaymentPreference.objects.filter(
                **pref_args)
        else:
            payment_pref_list = None
            if unknown_msg:
                pref_args['provider_system_id'] = unknown_msg
            else:
                pref_args.pop('provider_system_id')
        if not payment_pref_list:
            pref = PaymentPreference(**pref_args)
            pref.tier_id = 1
            pref.save()
        else:
            pref = payment_pref_list[0]
        pref.secondary_identifier = \
            name_on_card if name_on_card else unknown_msg
        if all([payment_method in settings.SAFE_CHARGE_IMMEDIATE_METHODS,
                unique_cc,
                name_on_card]):
            pref.is_immediate_payment = True
        if push_request:
            pref.push_request = push_request
        pref.save()
        set_preference_bank_bin_invoke.apply_async(
            [pref.pk],
            countdown=settings.FAST_TASKS_TIME_LIMIT
        )
        return pref

    def _prepare_payment_data(self, order, payment_preference, total_amount,
                              currency, ppp_tx_id, tx_id, auth_code):
        return {
            'order': order,
            'payment_preference': payment_preference,
            'amount_cash': Decimal(total_amount),
            'currency': Currency.objects.get(code=currency),
            'user': order.user,
            'payment_system_id': ppp_tx_id if ppp_tx_id else None,
            'secondary_payment_system_id': tx_id if tx_id else None,
            'type': Payment.DEPOSIT,
            'reference': order.unique_reference,
            'auth_code': auth_code
        }

    def _create_push_request(self, request):
        payload = request.POST.dict()
        ip = get_client_ip(request)
        valid_ip = ip_in_iplist(ip, settings.SAFE_CHARGE_ALLOWED_DMN_IPS)
        push_request = PushRequest(
            ip=ip,
            valid_ip=valid_ip,
            url=request.path_info
        )
        if settings.DATABASES.get(
                'default', {}).get('ENGINE') == 'django.db.backends.sqlite3':
            push_request.payload = payload
        else:
            push_request.payload_json = payload
        push_request.save()
        return push_request

    def _validate_safecharge_timestamp(self, response_ts, local_ts):
        if not response_ts:
            return False
        local_timestamp = local_ts.timestamp()
        response_timestamp = datetime.strptime(
            response_ts,
            '%Y-%m-%d.%H:%M:%S'
        ).timestamp()
        time_diff = local_timestamp - response_timestamp
        allowed_diff = settings.\
            SAFE_CHARGE_ALLOWED_REQUEST_TIME_STAMP_DIFFERENCE_SECONDS
        if abs(time_diff) >= allowed_diff:
            return False
        return True

    def post(self, request):
        params = request.POST
        key = settings.SAFE_CHARGE_SECRET_KEY
        total_amount = params.get('totalAmount', '')
        currency = params.get('currency', '')
        time_stamp = params.get('responseTimeStamp', '')
        ppp_tx_id = params.get('PPP_TransactionID', '')
        tx_id = params.get('TransactionID', '')
        status = params.get('Status', '')
        product_id = params.get('productId', '').replace(" ", "")
        unique_cc = params.get('uniqueCC', '')
        name_on_card = params.get('nameOnCard', '')
        checksum = params.get('advancedResponseChecksum',
                              params.get('advanceResponseChecksum', ''))
        to_hash = (key, total_amount, currency, time_stamp, ppp_tx_id, status,
                   product_id)
        auth_code = params.get('AuthCode', '')
        payment_method = params.get('payment_method', '')
        expected_checksum = get_sha256_sign(ar_hash=to_hash, delimiter='',
                                            upper=False)
        push_request = self._create_push_request(request)
        push_request.valid_timestamp = self._validate_safecharge_timestamp(
            time_stamp,
            push_request.created_on
        )
        push_request.valid_checksum = expected_checksum == checksum
        push_request.save()
        if push_request.is_valid:
            payment = None
            order = Order.objects.get(unique_reference=product_id)
            if all([status in ['APPROVED', 'SUCCESS', 'PENDING'],
                    order.status == Order.INITIAL]):
                pref = self.get_or_create_payment_preference(
                    unique_cc,
                    name_on_card,
                    product_id,
                    payment_method,
                    push_request=push_request
                )
                payment_data = self._prepare_payment_data(
                    order, pref, total_amount, currency, ppp_tx_id, tx_id,
                    auth_code
                )
                res = order.register_deposit(payment_data, crypto=False)
                if res.get('status') == 'OK':
                    push_request.payment_created = True
                    push_request.save()
                    order_cover_invoke.apply_async([order.pk])
                set_preference_for_verifications_invoke.apply([pref.pk])
            if all([status in ['APPROVED', 'SUCCESS'],
                    order.status == Order.PAID_UNCONFIRMED]):
                if not payment:
                    payment = order.payment_set.get(type=Payment.DEPOSIT)
                payment.is_success = True
                payment.save()
            if all([status in ['APPROVED', 'SUCCESS', 'PENDING']]):
                if not payment:
                    payment = order.payment_set.get(type=Payment.DEPOSIT)
                push_request.payment = payment
                push_request.save()
            return HttpResponse()
        return HttpResponseBadRequest()
