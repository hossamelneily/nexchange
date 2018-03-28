# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required

from django.core.urlresolvers import reverse
from django.http import (HttpResponseNotFound, HttpResponse, JsonResponse,
                         HttpResponseRedirect, HttpResponseForbidden)
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from nexchange.utils import get_nexchange_logger, get_client_ip
from core.models import Currency
from orders.models import Order
from payments.adapters import (leupay_adapter, robokassa_adapter,
                               unitpay_adapter, okpay_adapter,
                               payeer_adapter, sofort_adapter,
                               adv_cash_adapter)
from payments.models import Payment, PaymentPreference, PaymentMethod,\
    PushRequest
from payments.utils import get_sha256_sign
from payments.task_summary import run_payeer, run_okpay, run_sofort, \
    run_adv_cash
from decimal import Decimal
from payments.api_clients.card_pmt import CardPmtAPIClient
from core.context_processors import country_code
from django.views.generic import View
from django.utils.decorators import method_decorator
from datetime import datetime
from nexchange.utils import ip_in_iplist


@login_required
def payment_failure(request, provider):
    get_template('orders/partials/steps/step_retry_payment.html')
    # TODO: Better logic
    last_order = Order.objects.filter(user=request.user).latest('id')
    url = reverse('orders.add_order', kwargs={'pair': last_order.pair.name})
    last_order.status = Order.CANCELED
    last_order.save()
    return HttpResponseRedirect(url)


@login_required
def payment_retry(request):
    old_order = Order.objects.filter(user=request.user,
                                     status=Order.CANCELED).latest('id')
    order = old_order
    order.id = None
    order.save()
    url = '/'  # root
    # geturl_robokassa(order.id, str(order.amount_cash))
    return redirect(url)


def respond_retry(request):
    template = \
        get_template('orders/partials/steps/step_retry_payment.html')
    return HttpResponse(template.render({'bad_sugnature': True},
                                        request))


def payment_success(request, provider):
    logger = get_nexchange_logger(__name__)

    # TODO: this can be a decorator or middleware
    def flip_extension(host, resource, protocol='https',
                       query='redirect'):
        # solution with payeer working only for .co.uk
        site_name = host.split('.')[:1]
        full_host = '{}{}{}?{}=1'.format(
            site_name,
            '.co.uk' if host.endswith('.ru') else '.ru',
            resource,
            query
        )
        return '{}://{}'.format(protocol, full_host)

    if not request.user.is_authenticated():
        if 'redirect' not in request.GET:
            redirect_url = flip_extension(
                request.get_host(),
                request.path
            )
            logger.info('User is not authenticated '
                        'redirecting to {}'
                        .format(redirect_url))
            return HttpResponseRedirect(redirect_url)
        else:
            logger.info('User is still not authenticated '
                        'after redirect to {} request: {}'
                        .format(request.META['HTTP_HOST'],
                                request.__dict__))
    received_order = None
    if provider == 'robokassa':
        received_order = robokassa_adapter(request)
    elif provider == 'unitpay':
        received_order = unitpay_adapter(request)
    elif provider == 'leupay':
        received_order = leupay_adapter(request)
    elif provider == 'okpay':
        received_order = okpay_adapter(request)
    elif provider == 'payeer':
        received_order = payeer_adapter(request)
    elif provider == 'sofort':
        received_order = sofort_adapter(request)
    elif provider == 'advcash':
        received_order = adv_cash_adapter(request)

    # hacky hack
    supporterd = ['okpay', 'payeer', 'sofort', 'advcash']

    if provider not in supporterd:
        logger.error('Success view provider '
                     '{} not supported!'.format(provider))
    else:
        res = None
        if provider == 'payeer':
            res = run_payeer.apply_async(
                countdown=settings.GATEWAY_RESOLVE_TIME
            )
        elif provider == 'okpay':
            res = run_okpay.apply_async(
                countdown=settings.GATEWAY_RESOLVE_TIME
            )
        elif provider == 'sofort':
            res = run_sofort.apply_async(
                countdown=settings.GATEWAY_RESOLVE_TIME
            )
        elif provider == 'advcash':
            res = run_adv_cash.apply_async(
                countdown=settings.GATEWAY_RESOLVE_TIME
            )
        logger.info('Triggered payeer payment import for {}'.format(provider))
        if res.state == 'SUCCESS':
            logger.info('SUCCESS import payments from success callback')
        else:
            logger.error('{} state import payments from success callback'
                         'traceback: {}'.format(res.state, res.traceback))

    logger.info('User at {} success view.'
                'request: {} user: {}'
                .format(provider,
                        request.__dict__,
                        request.user.__dict__))

    if not received_order:
        logger.error('Success view without a provider request: '
                     '{} not found!'.format(request.__dict__))
        return HttpResponseNotFound(_('Unsupported payment provider'))

    lookup = {'user': request.user}
    if received_order.get('order_id'):
        lookup['unique_reference'] = \
            received_order['order_id']
    order = Order.objects.filter(**lookup).latest('id')

    if not order:
        logger.error('Success view provider request '
                     '{} not found!'.format(request.__dict__))
        return respond_retry(request)

    if not received_order.get('valid'):
        logger.error('Success view invalid payment request '
                     '{} not found!'.format(request.__dict__))
        return respond_retry(request)

    # This is only a provisional
    # flag which the user can set himself
    # does not affect business logic, only visual
    order.system_marked_as_paid = True
    order.save()

    # TODO: check signature
    # TODO: check api async for payment (optimization)
    redirect_url = "{}?oid={}&is_paid=true".\
        format(reverse('orders.orders_list'), order.unique_reference)
    logger.info('User at {} success view.'
                'request: {} user: {} redirected'
                'to order {}'
                .format(provider,
                        request.__dict__,
                        request.user.__dict__,
                        order.id))
    return redirect(redirect_url)


def payment_info(request, provider):
    assert provider
    pass


def payment_type(request):
    def get_pref_by_name(name, _currency):
        c_code = country_code(request)['COUNTRY_CODE']
        domain_code = request.META['HTTP_HOST'].split('.')[-1]
        possible_payment_countries = [c_code, domain_code.upper()]

        if not _currency:
            return None

        curr_objs = Currency.objects.filter(code=_currency.upper())
        if len(curr_objs) == 0:
            return None
        else:
            curr_obj = curr_objs[0]
        cards = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        if len(cards):
            card = cards[0]
            allowed_countries = card.payment_method.allowed_countries.all()
            if len(allowed_countries) > 0:
                allowed_list = [c.country.code for c in allowed_countries]
                for pos in possible_payment_countries:
                    if pos in allowed_list:
                        break
                else:
                    return None
        else:
            return None
        return card

    template = get_template('payments/partials/modals/payment_type.html')
    currency = request.POST.get('currency')

    categories = {
        'featured': {},  # Featured by country
        'credit_cards': {
            'visa': get_pref_by_name('Visa-internal', currency),
            'mastercard': get_pref_by_name('Mastercard-internal', currency),
            'virtual_mastercard': get_pref_by_name(
                'Mastercard-virtual', currency),
        },
        'banks': {
            'sber': get_pref_by_name('Sber', currency),
            'alfa': get_pref_by_name('Alfa', currency),
            'sepa': get_pref_by_name('SEPA', currency),
            'swift': get_pref_by_name('SWIFT', currency),
            'c2c': get_pref_by_name('c2c', currency),
            'sofort': get_pref_by_name('sofort', currency)
        },
        'wallets': {
            'qiwi': get_pref_by_name('Qiwi', currency),
            'skrill': get_pref_by_name('Skrill', currency),
            'paypal': get_pref_by_name('PayPal', currency),
            'okpay': get_pref_by_name('Okpay', currency),
            'payeer': get_pref_by_name('Payeer', currency),
            'adv_cash': get_pref_by_name('Advanced', currency),
        },
    }

    local_vars = {
        'categories': categories,
        'type': 'buy',
        'currency': currency.upper(),
    }
    translation.activate(request.POST.get('_locale'))
    return HttpResponse(template.render(local_vars,
                                        request))


@csrf_exempt
def payment_type_json(request):
    def get_pref_by_name(name, _currency):
        curr_obj = Currency.objects.get(code=_currency.upper())
        card = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        return card[0].identifier if len(card) else 'None'

    currency = request.POST.get('currency')

    cards = {
        'sber': get_pref_by_name('Sber', currency),
        'alfa': get_pref_by_name('Alfa', currency),
        'qiwi': get_pref_by_name('Qiwi', currency),
        'sepa': get_pref_by_name('SEPA', currency),
        'swift': get_pref_by_name('SWIFT', currency),
        'paypal': get_pref_by_name('PayPal', currency),
        'okpay': get_pref_by_name('Okpay', currency),

    }

    return JsonResponse({'cards': cards})


def payeer_status(request):
    if request.META['REMOTE_ADDR'] not in settings.PAYEER_IPS:
        return HttpResponseNotFound(_('Resource not found'))
    if not request.method == 'POST':
        return HttpResponseNotFound(_('Resource not found'))
    retval = 'error'
    try:
        ar_hash = (
            request.POST['m_operation_id'],
            request.POST['m_operation_ps'],
            request.POST['m_operation_date'],
            request.POST['m_operation_pay_date'],
            request.POST['m_shop'],
            request.POST['m_orderid'],
            request.POST['m_amount'],
            request.POST['m_curr'],
            request.POST['m_desc'],
            request.POST['m_status'],
            settings.PAYEER_IPN_KEY
        )
        sign = get_sha256_sign(ar_hash=ar_hash)
        if (request.POST.get('m_sign') == sign and
                request.POST.get('m_status') == 'success'):
            retval = request.POST['m_orderid'] + '|success'

            o_list = Order.objects.filter(
                amount_quote=Decimal(request.POST['m_amount']),
                unique_reference=request.POST['m_orderid'],
                pair__quote__code=request.POST['m_curr']
            )
            if len(o_list) == 1:
                o = o_list[0]
                Payment.objects.get_or_create(
                    amount_cash=Decimal(request.POST['m_amount']),
                    user=o.user,
                    order=o,
                    reference=o.unique_reference,
                    payment_preference=o.payment_preference,
                    currency=o.pair.quote
                )
        else:
            retval = request.POST['m_orderid'] + '|error'
    except KeyError:
        pass
    return HttpResponse(retval)


@login_required
@csrf_exempt
def pay_with_credit_card(request):
    client = CardPmtAPIClient()
    ip = get_client_ip(request)
    params = request.POST
    params_dict = {'ip': ip}
    for key in params:
        if len(params[key]) != 0:
            params_dict.update({key: params[key]})
    params_dict['ccexp'] = params_dict['ccexp'].replace('/', '').\
        replace(' ', '')
    params_dict['ccn'] = params_dict['ccn'].replace(' ', '')
    params_dict['phone'] = params_dict['phone'].replace(' ', '')
    res = client.pay_for_the_order(**params_dict)
    if res['status'] == 1:
        redirect_url = reverse('orders.orders_list') + '?oid={}'.format(
            params_dict['orderid']
        )
        return JsonResponse({'status': 'OK', 'redirect': redirect_url},
                            safe=False)
    else:
        return HttpResponseForbidden(_(res['msg']))


class SafeChargeListenView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SafeChargeListenView, self).dispatch(request,
                                                          *args, **kwargs)

    def get_or_create_payment_preference(self, unique_cc, name_on_card,
                                         product_id, payment_method):
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
        else:
            pref = payment_pref_list[0]
        pref.secondary_identifier = \
            name_on_card if name_on_card else unknown_msg
        if all([payment_method in settings.SAFE_CHARGE_IMMEDIATE_METHODS,
                unique_cc,
                name_on_card]):
            pref.is_immediate_payment = True
        pref.save()
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
                pref = self.get_or_create_payment_preference(unique_cc,
                                                             name_on_card,
                                                             product_id,
                                                             payment_method)
                payment_data = self._prepare_payment_data(
                    order, pref, total_amount, currency, ppp_tx_id, tx_id,
                    auth_code
                )
                res = order.register_deposit(payment_data, crypto=False)
                if res.get('status') == 'OK':
                    push_request.payment_created = True
                    push_request.save()
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
