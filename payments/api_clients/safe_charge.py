from payments.api_clients.base import BasePaymentApi
from datetime import datetime
import json
import requests
from payments.utils import get_sha256_sign
from payments.models import PaymentPreference, PaymentMethod, Payment
from django.conf import settings
from copy import deepcopy
from django.core.exceptions import ValidationError
from payments.utils import money_format
from urllib.parse import quote


class SafeCharge:

    def __init__(self, merchant_id=None, merchant_site_id=None,
                 secret_key=None, test=False):
        test_url = 'https://ppp-test.safecharge.com/ppp/{}.do'
        prod_url = 'https://secure.safecharge.com/ppp/{}.do'
        self.url = test_url if test else prod_url
        self.merchant_id = merchant_id
        self.merchant_site_id = merchant_site_id
        self.secret_key = secret_key
        self.body = {
            'merchantId': self.merchant_id,
            'merchantSiteId': self.merchant_site_id,
        }

    def _get_timestamp(self):
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _check_fields(self, mandatory_fields, **fields):
        for field in mandatory_fields:
            if field not in fields:
                raise ValidationError(
                    'Missing mandatory field {}'.format(field))

    def _get_checksum(self, checksum_fields, **kwargs):
        time_stamp = self._get_timestamp()
        from_kw = [kwargs.get(k, '') for k in checksum_fields]
        to_hash = \
            [self.merchant_id, self.merchant_site_id] + from_kw \
            + [time_stamp, self.secret_key]
        checksum = get_sha256_sign(ar_hash=tuple(to_hash),
                                   upper=False, delimiter='')
        return checksum, time_stamp

    def _get_body(self, time_stamp, checksum, **kwargs):
        body = deepcopy(self.body)
        body.update(kwargs)
        body.update({
            'timeStamp': time_stamp,
            'checksum': checksum
        })
        return json.dumps(body)

    def _get_headers(self, body):
        return {
            'Content-Type': 'application/json',
            'Content-Length': str(len(body))
        }

    def getSessionToken(self, **kwargs):
        endpoint = 'api/v1/getSessionToken'
        mandatory_fields = ['clientRequestId']
        checksum_fields = ['clientRequestId']
        self._check_fields(mandatory_fields, **kwargs)
        checksum, time_stamp = self._get_checksum(checksum_fields, **kwargs)
        body = self._get_body(time_stamp, checksum, **kwargs)
        headers = self._get_headers(body)
        url = self.url.format(endpoint)
        res = requests.post(url, headers=headers, data=body)
        return res.json()

    def _request(self, endpoint, mandatory_fields, mandatory_tree_fields,
                 checksum_fields, **kwargs):
        self._check_fields(mandatory_fields, **kwargs)
        for key, value in mandatory_tree_fields.items():
            self._check_fields(value, **kwargs[key])
        checksum, time_stamp = self._get_checksum(checksum_fields, **kwargs)
        body = self._get_body(time_stamp, checksum, **kwargs)
        headers = self._get_headers(body)
        url = self.url.format(endpoint)
        res = requests.post(url, headers=headers, data=body)
        return res.json()

    def dynamic3D(self, **kwargs):
        endpoint = 'api/v1/dynamic3D'
        mandatory_fields = [
            'sessionToken', 'currency', 'amount', 'cardData', 'clientRequestId'
        ]
        mandatory_tree_fields = {'cardData': [
            'cardNumber', 'cardHolderName', 'expirationMonth',
            'expirationYear', 'CVV'
        ]}
        checksum_fields = ['clientRequestId', 'amount', 'currency']
        return self._request(endpoint, mandatory_fields,
                             mandatory_tree_fields, checksum_fields, **kwargs)

    def refundTransaction(self, **kwargs):
        endpoint = 'api/v1/refundTransaction'
        mandatory_fields = [
            'currency', 'amount', 'clientRequestId', 'clientUniqueId',
            'relatedTransactionId', 'authCode'
        ]
        mandatory_tree_fields = {}
        checksum_fields = ['clientRequestId', 'clientUniqueId', 'amount',
                           'currency', 'relatedTransactionId', 'authCode',
                           'comment', 'urlDetails']
        return self._request(endpoint, mandatory_fields,
                             mandatory_tree_fields, checksum_fields, **kwargs)

    def voidTransaction(self, **kwargs):
        endpoint = 'api/v1/voidTransaction'
        mandatory_fields = [
            'currency', 'amount', 'clientRequestId', 'clientUniqueId',
            'relatedTransactionId', 'authCode'
        ]
        mandatory_tree_fields = {}
        checksum_fields = ['clientRequestId', 'clientUniqueId', 'amount',
                           'currency', 'relatedTransactionId', 'authCode',
                           'comment', 'urlDetails']
        return self._request(endpoint, mandatory_fields,
                             mandatory_tree_fields, checksum_fields, **kwargs)

    def purchase(self, **kwargs):
        endpoint = 'api/v1/purchase'
        mandatory_fields = [
        ]
        mandatory_tree_fields = {}
        checksum_fields = []
        return self._request(endpoint, mandatory_fields,
                             mandatory_tree_fields, checksum_fields, **kwargs)

    def payment3D(self, **kwargs):
        endpoint = 'api/v1/payment3D'
        mandatory_fields = [
            'sessionToken', 'currency', 'amount', 'cardData',
            'clientRequestId', 'orderId', 'transactionType'
        ]
        mandatory_tree_fields = {'cardData': [
            'cardNumber', 'cardHolderName', 'expirationMonth',
            'expirationYear', 'CVV'
        ]}
        checksum_fields = ['clientRequestId', 'amount', 'currency']
        return self._request(endpoint, mandatory_fields,
                             mandatory_tree_fields, checksum_fields, **kwargs)


class SafeChargeAPIClient(BasePaymentApi):

    def __init__(self):
        super(SafeChargeAPIClient, self).__init__()
        self.api = SafeCharge(
            merchant_id=settings.SAFE_CHARGE_MERCHANT_ID,
            merchant_site_id=settings.SAFE_CHARGE_MERCHANT_SITE_ID,
            secret_key=settings.SAFE_CHARGE_SECRET_KEY,
            test=settings.SAFE_CHARGE_TEST
        )
        self.name = 'Safe Charge'
        self.payment_method = None

    def get_payment_method(self):
        if not self.payment_method:
            self.payment_method = PaymentMethod.objects.get(
                name__icontains=self.name
            )

    def generate_cachier_url_for_order(self, order):
        url = self.api.url.format('purchase')
        _ref = order.unique_reference

        key = settings.SAFE_CHARGE_SECRET_KEY
        merchant_id = settings.SAFE_CHARGE_MERCHANT_ID
        merchant_site_id = settings.SAFE_CHARGE_MERCHANT_SITE_ID
        currency = order.pair.quote.code
        amount = str(money_format(order.amount_quote, places=2))
        total_amount = item_amount_1 = amount
        email = 'user{}@nexchange.io'.format(order.user.pk)
        item_name_1 = _ref
        item_quantity_1 = '1'
        user_token = 'auto'
        version = '4.0.0'
        user_token_id = order.user.username
        notify_url = settings.SAFE_CHARGE_NOTIFY_URL
        success_url = settings.SAFE_CHARGE_SUCCESS_URL.format(_ref)
        pending_url = settings.SAFE_CHARGE_PENDING_URL.format(_ref)
        error_url = settings.SAFE_CHARGE_ERROR_URL.format(_ref)
        back_url = settings.SAFE_CHARGE_BACK_URL.format(_ref)
        time_stamp = datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
        to_hash = (key, merchant_site_id, merchant_id, currency, total_amount,
                   email,
                   item_name_1, item_amount_1, item_quantity_1, user_token,
                   version, user_token_id, success_url, pending_url,
                   error_url, back_url, notify_url, time_stamp)
        checksum = get_sha256_sign(ar_hash=to_hash, delimiter='', upper=False)
        params = \
            '?merchant_site_id={merchant_site_id}' \
            '&merchant_id={merchant_id}' \
            '&currency={currency}' \
            '&total_amount={total_amount}' \
            '&email={email}' \
            '&item_name_1={item_name_1}' \
            '&item_amount_1={item_amount_1}' \
            '&item_quantity_1={item_quantity_1}' \
            '&user_token={user_token}' \
            '&version={version}' \
            '&user_token_id={user_token_id}' \
            '&success_url={success_url}' \
            '&pending_url={pending_url}' \
            '&error_url={error_url}' \
            '&back_url={back_url}' \
            '&notify_url={notify_url}' \
            '&time_stamp={time_stamp}' \
            '&checksum={checksum}'.format(
                merchant_site_id=merchant_site_id,
                merchant_id=merchant_id,
                time_stamp=time_stamp,
                total_amount=total_amount,
                email=quote(email),
                currency=currency,
                checksum=checksum,
                item_name_1=item_name_1,
                item_amount_1=item_amount_1,
                item_quantity_1=item_quantity_1,
                user_token_id=user_token_id,
                user_token=user_token,
                version=version,
                success_url=quote(success_url),
                pending_url=quote(pending_url),
                error_url=quote(error_url),
                back_url=quote(back_url),
                notify_url=quote(notify_url)
            )
        url = url + params
        return url

    def _prepare_request_data(self, order, payment, **kwargs):
        kwargs['merchantDetails'] = kwargs.get('merchantDetails', {})
        kwargs['merchantDetails'].update(
            {'customField1': order.unique_reference}
        )
        amount = money_format(order.amount_quote, places=2)
        kwargs.update({
            'amount': str(amount),
            'currency': order.pair.quote.code,
            'isDynamic3D': '1',
            'dynamic3DMode': 'ON',
        })
        if order.status == order.PAID_UNCONFIRMED:
            pref = payment.payment_preference
            ccexp = pref.ccexp.split('/')
            kwargs.update({
                'cardData': {
                    'cardNumber': pref.identifier,
                    'cardHolderName': pref.secondary_identifier,
                    'expirationMonth': ccexp[0],
                    'expirationYear': ccexp[1],
                    'CVV': pref.cvv
                },
                'orderId': payment.payment_system_id,
                'transactionType': 'Auth'
            })
        return kwargs

    def create_payment_preference(self, order, **kwargs):
        self.get_payment_method()
        card_data = kwargs.get('cardData', {})
        identifier = card_data.get('cardNumber')
        secondary_identifier = card_data.get('cardHolderName')
        cvv = card_data.get('CVV')
        ccexp = '{}/{}'.format(
            card_data.get('expirationMonth'),
            card_data.get('expirationYear'),
        )
        user = order.user if order else None
        filters = {
            'payment_method': self.payment_method,
            'user': user
        }
        pref1_filters = deepcopy(filters)
        pref1_filters.update({'identifier': identifier})
        pref1 = PaymentPreference.objects.filter(
            **pref1_filters
        )
        pref2_filters = deepcopy(filters)
        pref1_filters.update(
            {'secondary_identifier': secondary_identifier}
        )

        pref2 = PaymentPreference.objects.filter(
            **pref2_filters
        )
        new_pref = not pref1 and not pref2
        if pref1 and pref2 and pref1[0] != pref2[0]:
            self.logger.error('found duplicate payment preferences {} {}'
                              .format(pref1, pref2))
        if new_pref:
            # creating a pref without a user, after payment
            # will be matched with an order we will assign it
            # to the user who made the order
            pref = PaymentPreference.objects.create(
                identifier=identifier,
                secondary_identifier=secondary_identifier,
                payment_method=self.payment_method,
                cvv=cvv,
                ccexp=ccexp,
                user=user
            )

            self.logger.info(
                'payment preference created {} {} {}'.format(
                    pref, identifier, secondary_identifier))
        else:
            pref = pref1[0] if pref1 else pref2[0]
        return pref

    def _prepare_payment_data(self, order, payment_preference, **kwargs):
        return {
            'order': order,
            'payment_preference': payment_preference,
            'user': order.user,
            'payment_system_id': kwargs.get('orderId'),
            'secondary_payment_system_id': kwargs.get('transactionId'),
            'type': Payment.DEPOSIT,
            'amount_cash': order.amount_quote,
            'currency': order.pair.quote,
            'reference': order.unique_reference,
            'is_success': True
        }

    def _register_payment(self, order, **kwargs):
        payment_preference = self.create_payment_preference(order, **kwargs)
        params = self._prepare_request_data(order, None, **kwargs)
        res = self.api.dynamic3D(**params)
        if all([res['status'] == 'SUCCESS',
                res['transactionStatus'] == 'APPROVED']):
            payment_data = self._prepare_payment_data(
                order, payment_preference, **res)
            order.register_deposit(payment_data, crypto=False)
        return res

    def _confirm_payment(self, payment, **kwargs):
        order = payment.order
        params = self._prepare_request_data(order, payment, **kwargs)
        res = self.api.payment3D(**params)
        if all([res['status'] == 'SUCCESS',
                res['transactionStatus'] == 'APPROVED']):
            order.confirm_deposit(payment, crypto=False)
        return res

    def refund_payment(self, payment):
        if not payment.is_success:
            return False
        order = payment.order
        if not order:
            return False
        if order.status != order.PAID_UNCONFIRMED:
            return False
        params = {
            'currency': payment.currency.code,
            'amount': str(money_format(payment.amount_cash, places=2)),
            'clientRequestId': 'refund_{}'.format(order.unique_reference),
            'clientUniqueId': 'refund_{}'.format(order.unique_reference),
            'relatedTransactionId': payment.secondary_payment_system_id,
            'authCode': payment.auth_code
        }
        res = self.api.refundTransaction(**params)
        status = res.get('transactionStatus', '')
        if status != 'APPROVED':
            return False
        order.cancel()
        payment.is_success = False
        payment.save()
        payment.flag(val=res)
        return True
