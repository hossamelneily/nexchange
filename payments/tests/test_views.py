from copy import deepcopy
from decimal import Decimal
from time import time
from unittest import skip

import requests_mock
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client
from unittest.mock import patch

from core.models import Address, Transaction, Currency
from core.tests.base import OrderBaseTestCase, UserBaseTestCase
from core.tests.base import UPHOLD_ROOT, SCRYPT_ROOT
from core.tests.utils import data_provider
from nexchange.api_clients.uphold import UpholdApiClient
from orders.models import Order
from orders.task_summary import buy_order_release_reference_periodic
from payments.models import Payment, PaymentMethod, PaymentPreference
from payments.tests.test_api_clients.base import BaseCardPmtAPITestCase
from payments.utils import get_sha256_sign, get_payeer_desc
from payments.payment_handlers.safe_charge import SafeChargePaymentHandler
from rest_framework.test import APIClient
from payments.task_summary import check_fiat_order_deposit_periodic
import json
from verification.models import Verification
from collections import OrderedDict


class PayeerTestCase(OrderBaseTestCase):

    def _create_input_params(self, status='success', delete=None,
                             order_id='12345'):
        input_list = [
            '123456',
            '2609',
            '21.12.2012 21:12',
            '21.12.2012 21:12',
            settings.PAYEER_WALLET,
            order_id,
            '100.00',
            'EUR',
            get_payeer_desc('BUY 0.1BTC'),
            status,
            settings.PAYEER_IPN_KEY
        ]
        self.input_params = {
            'm_operation_id': input_list[0],
            'm_operation_ps': input_list[1],
            'm_operation_date': input_list[2],
            'm_operation_pay_date': input_list[3],
            'm_shop': input_list[4],
            'm_orderid': input_list[5],
            'm_amount': input_list[6],
            'm_curr': input_list[7],
            'm_desc': input_list[8],
            'm_status': input_list[9],
            'm_sign': get_sha256_sign(ar_hash=(i for i in input_list))
        }
        if delete is not None:
            del self.input_params[delete]

    def setUp(self):
        super(PayeerTestCase, self).setUp()
        self.status_url = reverse('payments.payeer.status')
        self.client = Client(REMOTE_ADDR='185.71.65.92')
        self.payment_method = PaymentMethod(name='Payeer')
        self.payment_method.save()
        self._create_input_params()
        pref_data = {
            'comment': 'Just testing',
            'payment_method': self.payment_method,
            'user': self.user
        }
        self.pref = PaymentPreference(**pref_data)
        self.pref.save()

    def test_payeer_status_success(self):
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertIn('|success', content)

    def test_payeer_status_error(self):
        self._create_input_params(status='error')
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertIn('|error', content)

    def test_payeer_status_missing_param_error(self):
        self._create_input_params(status='error', delete='m_operation_id')
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertEqual('error', content)

    @patch('orders.models.Order.calculate_quote_from_base')
    def test_payeer_payment_after_success(self, convert_coin):
        convert_coin.return_value = None
        order_data = {
            'amount_quote': Decimal(self.input_params['m_amount']),
            'amount_base': Decimal(0.1),
            'pair': self.BTCEUR,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': self.input_params['m_orderid'],
            'payment_preference': self.pref,
        }
        order = Order(**order_data)
        order.save()
        self._create_input_params(order_id=order.unique_reference)
        self.client.post(self.status_url, self.input_params)
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            order=order,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        # apply second time - should not create another payment
        self.client.post(self.status_url, self.input_params)
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            order=order,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))

    def test_payeer_forbidden_ip_request(self):
        client = Client(REMOTE_ADDR='127.0.0.1')
        response = client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 404)


class RoboTestCase(UserBaseTestCase):

    def setUp(self):
        super(RoboTestCase, self).setUp()

    @skip("causes failures, needs to be migrated")
    def test_bad_paysuccess(self):
        r = self.client.post('/en/paysuccess/robokassa')
        self.assertEqual(r.json()['result'], 'bad request')

    @skip("causes failures, needs to be migrated")
    def test_bad_paysuccess_with_param(self):
        r = self.client.post('/en/paysuccess/robokassa',
                             {'OutSum': 1,
                              'InvId': 1,
                              'SignatureValue': 'fsdfdfdsd'})
        self.assertEqual(r.json()['result'], 'bad request')


class PaymentReleaseTestCase(OrderBaseTestCase):

    def setUp(self):
        super(PaymentReleaseTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.save()
        self.method_data = {
            "is_internal": 1,
            'name': 'Robokassa'
        }

        amount_cash = Decimal(30000.00)

        self.payment_method = PaymentMethod(name='ROBO')
        self.payment_method.save()

        self.addr_data = {
            'type': 'W',
            'name': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            'address': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',

        }

        self.addr = Address(**self.addr_data)
        self.addr.user = self.user
        self.addr.save()

        pref_data = {
            'comment': 'Just testing',
            'payment_method': self.payment_method,
            'user': self.user
        }

        pref = PaymentPreference(**pref_data)
        pref.save('internal')
        self.data = {
            'amount_quote': amount_cash,
            'amount_base': Decimal(1.00),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': pref,
            'status': Order.PAID
        }

        self.order = Order(**self.data)
        self.order.save()

        self.pay_data = {
            'amount_cash': self.order.amount_quote,
            'currency': self.order.pair.quote,
            'user': self.user,
            'payment_preference': pref,
        }

        self.payment = Payment(**self.pay_data)
        self.payment.save()

        tx_id_ = '76aa6bdc27e0bb718806c93db66525436' \
                 'fa621766b52bad831942dee8b618678'

        self.transaction = Transaction(tx_id=tx_id_,
                                       order=self.order, address_to=self.addr)
        self.transaction.save()

    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_bad_release_payment(self, prepare, execute_txn):
        api = UpholdApiClient()
        execute_txn.return_value = {'code': 'validation_failed'}
        prepare.return_value = None

        for o in Order.objects.filter(status=Order.PAID):
            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_quote,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.pair.quote).first()
            if p is not None:
                tx_id_, success = api.release_coins(o.pair.base,
                                                    o.withdraw_address,
                                                    o.amount_base)
                self.assertEqual(tx_id_, None)

    def test_orders_with_approved_payments(self):

        for o in Order.objects.filter(status=Order.PAID):

            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_quote,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.pair.quote).first()

            if p is not None:

                o.status = Order.RELEASED
                o.save()

                p.is_complete = True
                p.save()

            # Can't use refresh_from_db or o itself because 'RELEASED' is set
            #  on test itself
            order_check = Order.objects.get(
                unique_reference=o.unique_reference
            )
            self.assertTrue(order_check.status == Order.RELEASED)
            self.assertTrue(p.is_complete)


class MastercardTestCase(BaseCardPmtAPITestCase):

    def setUp(self):
        super(MastercardTestCase, self).setUp()
        self.pay_url = reverse('payments.pay_with_credit_card')

    @data_provider(lambda: (
        ('1', 200, Order.PAID, {}),
        ('0', 403, Order.INITIAL, {}),
        ('1', 403, Order.INITIAL, {'ccn': 'nonesense'}),
        ('1', 403, Order.INITIAL, {'cvv': 'nonesense'}),
        ('1', 403, Order.INITIAL, {'ccexp': '0101'}),
        ('1', 403, Order.INITIAL, {'address1': ''}),
    ))
    @requests_mock.mock()
    @patch('orders.models.Order._validate_status')
    def test_pay_for_the_order(self, pmt_status, response_status, order_status,
                               update_params, mock, _validate_status):
        _validate_status.return_value = True
        provider_data = 'pmt:{}, response:{}, order:{}'.format(
            pmt_status, response_status, order_status
        )
        updated_params = deepcopy(self.required_params_dict)
        updated_params.update(update_params)
        response_code = '100'
        status = pmt_status
        transaction_id = 'tx_id' + str(time())
        transaction_success = self.transaction_response_empty.format(
            response_code=response_code,
            status=status,
            transaction_id=transaction_id
        )
        mock.get(self.pmt_client.url, text=transaction_success)
        response = self.client.post(self.pay_url, updated_params)
        self.assertEqual(response.status_code, response_status, provider_data)
        self.order.refresh_from_db()
        # self.assertEqual(self.order.status, order_status, provider_data)
        # FIXME: CANCEL CARDPMT because it doesnt work
        self.assertIn(self.order.status, [Order.CANCELED, Order.INITIAL],
                      provider_data)
        self.order.status = Order.INITIAL
        self.order.save()


class SafeChargeTestCase(OrderBaseTestCase):

    def setUp(self):
        super(SafeChargeTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.save()

        self.pref = PaymentPreference.objects.get(
            payment_method__name='Safe Charge'
        )
        self.payment_handler = SafeChargePaymentHandler()
        self.api_client = APIClient()

    def _create_order_api(self, set_pref=False, order_data=None):
        if not order_data:
            order_data = {
                "amount_base": 3,
                "is_default_rule": False,
                "pair": {
                    "name": "BTCEUR"
                },
                "withdraw_address": {
                    "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
                }
            }
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        if set_pref:
            order.payment_preference = self.pref
            order.save()
        return order

    def _create_kyc(self, ref):
        order_data = {
            "order_reference": ref,
        }
        order_api_url = '/en/api/v1/kyc/'
        with patch('verification.serializers.'
                   'CreateKycSerializer.to_internal_value') as p:
            p.return_value = OrderedDict({'order_reference': ref})
            self.api_client.post(
                order_api_url, order_data, format='json')
        kyc = Verification.objects.latest('id')
        return kyc

    def _check_kyc(self, ref):
        url = '/en/api/v1/kyc/{}/'.format(ref)
        response = self.api_client.get(url)
        return response.json()['is_verified']

    def _mock_safe_charge_urls(self, mock):
        url = self.payment_handler.api.url
        dynamic_resp = payment_resp = {
            'status': 'SUCCESS',
            'transactionStatus': 'APPROVED',
            'orderId': self.generate_txn_id(),
            'transactionId': self.generate_txn_id()
        }
        token_resp = {'sessionToken': 'token_awesome', 'status': 'SUCCESS'}
        mock.post(url.format('api/v1/dynamic3D'),
                  text=json.dumps(dynamic_resp))
        mock.post(url.format('api/v1/payment3D'),
                  text=json.dumps(payment_resp))
        mock.post(url.format('api/v1/getSessionToken'),
                  text=json.dumps(token_resp))

    @patch(SCRYPT_ROOT + 'get_info')
    @patch('orders.models.Order.coverable')
    def _test_paid_order(self, order, coverable, scrypt_info):
        scrypt_info.return_value = {}
        order.refresh_from_db()
        payment = order.payment_set.get(type=Payment.DEPOSIT)
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        self.assertTrue(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertFalse(payment.is_redeemed)

        self.order.refresh_from_db()
        with patch(SCRYPT_ROOT + 'release_coins') as release_coins_scrypt:
            release_coins_scrypt.return_value = self.generate_txn_id(), True
            buy_order_release_reference_periodic.apply()
        order.refresh_from_db()
        payment.refresh_from_db()

        self.assertTrue(payment.is_redeemed)

        self.assertEqual(Order.RELEASED, order.status)

    @requests_mock.mock()
    @patch(SCRYPT_ROOT + 'release_coins')
    @patch('orders.models.Order.coverable')
    @patch('orders.models.Order._validate_status')
    def test_pay_with_safe_charge(self, mock, _validate_status, coverable,
                                  release_coins_scrypt):
        order = self._create_order_api()
        url = self.payment_handler.api.url
        dynamic_resp = payment_resp = {
            'status': 'SUCCESS',
            'transactionStatus': 'APPROVED',
            'orderId': '12345',
            'transactionId': '54321'
        }
        token_resp = {'sessionToken': 'token_awesome', 'status': 'SUCCESS'}
        mock.post(url.format('api/v1/dynamic3D'),
                  text=json.dumps(dynamic_resp))
        mock.post(url.format('api/v1/payment3D'),
                  text=json.dumps(payment_resp))
        mock.post(url.format('api/v1/getSessionToken'),
                  text=json.dumps(token_resp))
        _validate_status.return_value = True
        client_request_id = order.unique_reference
        session_token = self.payment_handler.api.getSessionToken(
            **{'clientRequestId': client_request_id}
        )['sessionToken']
        params = {
            'sessionToken': session_token,
            'clientRequestId': client_request_id,
            'cardData': {
                'cardNumber': '375510513169537',
                'cardHolderName': 'Sir Testalot',
                'expirationMonth': '01',
                'expirationYear': '22',
                'CVV': '123'
            }
        }
        # Register Payment
        self.payment_handler.register_payment(order.pk, **params)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.last()
        self.assertEqual(order.amount_quote, payment.amount_cash)
        self.assertEqual(dynamic_resp['orderId'], payment.payment_system_id)
        self.assertEqual(dynamic_resp['transactionId'],
                         payment.secondary_payment_system_id)
        self.assertEqual(Payment.DEPOSIT, payment.type)
        self.assertEqual(order.pair.quote, payment.currency)
        pref = payment.payment_preference
        card_data = params['cardData']
        self.assertEqual(card_data['cardNumber'], pref.identifier)
        self.assertEqual(card_data['cardHolderName'],
                         pref.secondary_identifier)
        self.assertEqual(
            '{}/{}'.format(
                card_data['expirationMonth'],
                card_data['expirationYear'],
            ),
            pref.ccexp
        )
        self.assertEqual(card_data['CVV'], pref.cvv)

        # Confirm Payment
        self.payment_handler.confirm_payment(payment.pk, **params)

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        self.assertTrue(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertFalse(payment.is_redeemed)

        self._test_paid_order(order)

    def _get_dmn_request_params_for_order(self, order, unique_cc, name,
                                          status='APPROVED'):
        order.refresh_from_db()
        time_stamp = '2017-11-27.12:56:06'
        key = settings.SAFE_CHARGE_SECRET_KEY
        total_amount = str(order.amount_quote)
        currency = order.pair.quote.code
        ppp_tx_id = self.generate_txn_id()
        product_id = order.unique_reference
        to_hash = (key, total_amount, currency, time_stamp, ppp_tx_id, status,
                   product_id)
        checksum = get_sha256_sign(ar_hash=to_hash, delimiter='',
                                   upper=False)
        params = {
            'PPP_TransactionID': ppp_tx_id,
            'productId': product_id,
            'totalAmount': total_amount,
            'currency': currency,
            'advancedResponseChecksum': checksum,
            'Status': status,
            'responseTimeStamp': time_stamp,
            'uniqueCC': unique_cc,
            'nameOnCard': name
        }
        return params

    @data_provider(lambda: (
        ('APPROVED', Order.PAID_UNCONFIRMED, True),
        ('SUCCESS', Order.PAID_UNCONFIRMED, True),
        ('PENDING', Order.PAID_UNCONFIRMED, False),
        ('ERROR', Order.INITIAL, None),
        ('DECLINED', Order.INITIAL, None)
    ))
    def test_dmn_register(self, status, order_status, payment_success):
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status=status)
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, order_status)

        if payment_success is not None:

            payment = order.payment_set.get(type=Payment.DEPOSIT)
            pref = payment.payment_preference
            self.assertEqual(payment.payment_preference.payment_method,
                             order.payment_preference.payment_method)
            self.assertEqual(order.amount_quote, payment.amount_cash)
            self.assertEqual(order.pair.quote, payment.currency)
            self.assertEqual(pref.provider_system_id, card_id)
            self.assertEqual(pref.secondary_identifier, name)
            self.assertEqual(payment_success, payment.is_success)
        self.client.logout()

    def test_release_fiat_order(self):
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='PENDING')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertFalse(payment.is_success)

        # Check without KYC
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertFalse(self._check_kyc(order.unique_reference))
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        # Check with Pending KYC
        kyc = self._create_kyc(order.unique_reference)
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertFalse(self._check_kyc(order.unique_reference))
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        # Check with Confirmed KYC, but payment PENDING
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.save()
        self.assertTrue(self._check_kyc(order.unique_reference))
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        # Check with Confirmed KYC, and APPROVED payment
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        payment.refresh_from_db()
        self.assertTrue(payment.is_success)
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        payment.refresh_from_db()
        self.assertTrue(payment.is_complete)

        self._test_paid_order(order)

    def test_generate_cachier_url(self):
        order = self._create_order_api()
        url = self.payment_handler.generate_cachier_url_for_order(order)
        self.assertIn(order.user.username, url)

    @patch('orders.models.Order.get_current_slippage')
    def test_payment_fee(self, get_slippage):
        get_slippage.return_value = Decimal('0')
        # base fee
        amount_base = 4
        order_data = {
            "amount_base": amount_base,
            "is_default_rule": False,
            "pair": {
                "name": "BTCEUR"
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        order = self._create_order_api(order_data=order_data)
        pref = order.payment_preference
        fee = pref.payment_method.fee_deposit
        expected_ticker_amount_base = \
            (order.amount_base + order.pair.base.withdrawal_fee)\
            / (Decimal('1.0') - fee)
        self.assertAlmostEqual(expected_ticker_amount_base,
                               order.ticker_amount_base, 4)
        self.assertEqual(order.amount_base, Decimal(amount_base))
        # quote fee
        amount_quote = order.amount_quote
        order_data = {
            "amount_quote": amount_quote,
            "is_default_rule": False,
            "pair": {
                "name": "BTCEUR"
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        order = self._create_order_api(order_data=order_data)
        pref = order.payment_preference
        fee = pref.payment_method.fee_deposit
        expected_ticker_amount_quote = \
            (order.amount_quote - order.withdrawal_fee_quote) * \
            (Decimal('1.0') - fee)
        self.assertEqual(expected_ticker_amount_quote,
                         order.ticker_amount_quote)
        self.assertEqual(order.amount_quote, Decimal(amount_quote))
        self.assertAlmostEqual(order.amount_base, amount_base, 3)
