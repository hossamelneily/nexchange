from decimal import Decimal

import requests_mock
from django.conf import settings
from django.urls import reverse
from unittest.mock import patch

from core.models import Address, Transaction, Currency
from core.tests.base import OrderBaseTestCase, VerificationBaseTestCase
from core.tests.base import UPHOLD_ROOT, SCRYPT_ROOT
from core.tests.utils import data_provider, enable_all_pairs
from nexchange.api_clients.uphold import UpholdApiClient
from orders.models import Order
from orders.task_summary import buy_order_release_reference_periodic
from payments.models import Payment, PaymentMethod, PaymentPreference,\
    PushRequest
from payments.payment_handlers.safe_charge import SafeChargePaymentHandler
from rest_framework.test import APIClient
from payments.task_summary import check_fiat_order_deposit_periodic,\
    check_payments_for_refund_periodic, check_payments_for_void_periodic
import json
from verification.models import Verification, VerificationTier, \
    VerificationCategory, CategoryRule, VerificationDocument
from collections import namedtuple
import datetime
from freezegun import freeze_time
from payments.views import SafeChargeListenView
from ticker.tests.base import TickerBaseTestCase

from PIL import Image
import tempfile
from verification.task_summary import check_kyc_names_periodic


class PaymentReleaseTestCase(OrderBaseTestCase):

    def setUp(self):
        super(PaymentReleaseTestCase, self).setUp()
        enable_all_pairs()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
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


do_not_refund_fiat_order_params = namedtuple(
    'do_not_refund_fiat_order_params',
    ['case_name', 'payment_data', 'tx_status', 'order_status']
)


class SafeChargeTestCase(TickerBaseTestCase, VerificationBaseTestCase):

    def setUp(self):
        super(SafeChargeTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()

        self.pref = PaymentPreference.objects.get(
            payment_method__name='Safe Charge'
        )
        self.payment_handler = SafeChargePaymentHandler()
        self.api_client = APIClient()

    def tearDown(self):
        VerificationDocument.objects.all().delete()
        super(SafeChargeTestCase, self).tearDown()

    def _check_bank_bin(self, payment_preference):
        self.assertEqual(payment_preference.bank_bin.bin,
                         self.bankbins_resp['bin'])
        bank_bin = payment_preference.bank_bin
        self.assertEqual(bank_bin.bank.name, self.bankbins_resp['bank'])
        self.assertEqual(bank_bin.card_company.name,
                         self.bankbins_resp['card'])
        self.assertEqual(bank_bin.card_type.name, self.bankbins_resp['type'])
        self.assertEqual(bank_bin.card_level.name, self.bankbins_resp['level'])
        bank = bank_bin.bank
        self.assertEqual(bank.country.country,
                         self.bankbins_resp['countrycode'])
        self.assertEqual(bank.website, self.bankbins_resp['website'])
        self.assertEqual(bank.phone, self.bankbins_resp['phone'])
        self.assertTrue(bank_bin.checked_external)

    def _create_image(self):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (10, 10), 'white')
            image.save(f, 'PNG')
        return open(f.name, 'rb')

    def _create_order_api(self, set_pref=False, order_data=None,
                          pair_name='BTCEUR',
                          address='17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ'):
        if not order_data:
            order_data = {
                "amount_quote": 100,
                "pair": {
                    "name": pair_name
                },
                "withdraw_address": {
                    "address": address
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

    @patch('verification.task_summary.send_email')
    def _create_kyc(self, ref, send_email):
        id_doc = self._create_image()
        util_doc = self._create_image()
        selfie = self._create_image()
        whitelist_selfie = self._create_image()
        order_data = {
            "order_reference": ref,
            "identity_document": id_doc,
            "utility_document": util_doc,
            "selfie": selfie,
            "whitelist_selfie": whitelist_selfie
        }
        order_api_url = '/en/api/v1/kyc/'
        self.api_client.post(
            order_api_url, order_data, format='multipart'
        )
        id_doc.close()
        util_doc.close()
        selfie.close()
        kyc = Verification.objects.latest('id')
        send_email.assert_called_once()
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
        kyc = payment.payment_preference.verification_set.last()
        self.assertEqual(order.status, Order.PAID)
        self.assertTrue(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertFalse(payment.is_redeemed)

        order.refresh_from_db()
        with patch(SCRYPT_ROOT + 'release_coins') as release_coins_scrypt:
            release_coins_scrypt.return_value = self.generate_txn_id(), True
            if kyc:
                kyc.flag(val='Before release')
                buy_order_release_reference_periodic.apply()
                order.refresh_from_db()
                self.assertEqual(Order.PAID, order.status)
                kyc.flagged = False
                kyc.save()
            buy_order_release_reference_periodic.apply()
        order.refresh_from_db()
        payment.refresh_from_db()

        if kyc:
            self.assertTrue(payment.is_redeemed)
            self.assertEqual(Order.RELEASED, order.status)
        else:
            self.assertFalse(payment.is_redeemed)
            self.assertEqual(Order.PAID, order.status)

    def test_new_payment_preference_if_no_provider_id(self):
        order_ref = 'DSFGS'
        view = SafeChargeListenView()
        pref1 = view.get_or_create_payment_preference('', '', '',
                                                      'apmgw_Giropay')
        pref2 = view.get_or_create_payment_preference('', '', '',
                                                      'apmgw_Giropay')
        pref3 = view.get_or_create_payment_preference('', '', order_ref,
                                                      'apmgw_Giropay')
        self.assertNotEqual(pref1, pref2)
        self.assertNotEqual(pref1, pref3)
        self.assertNotEqual(pref2, pref3)
        self.assertEqual(pref1.payment_method, pref2.payment_method)
        self.assertIn('Safe Charge', pref1.payment_method.name)
        for pref in [pref1, pref2]:
            self.assertEqual(pref.secondary_identifier, '')
            self.assertIsNone(pref.provider_system_id)
            self.assertFalse(pref.is_immediate_payment)
        self.assertIn(order_ref, pref3.secondary_identifier)
        self.assertIn(order_ref, pref3.provider_system_id)
        self.assertFalse(pref3.is_immediate_payment)

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

    @data_provider(lambda: (
        ('APPROVED', Order.PAID_UNCONFIRMED, True),
        ('SUCCESS', Order.PAID_UNCONFIRMED, True),
        ('PENDING', Order.PAID_UNCONFIRMED, False),
        ('ERROR', Order.INITIAL, None),
        ('DECLINED', Order.INITIAL, None)
    ))
    @patch('payments.views.get_client_ip')
    def test_dmn_register(self, status, order_status, payment_success,
                          get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[2].split('-')[0]
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
            push_request = PushRequest.objects.get(payment=payment)
            self.assertEqual(pref.push_request, push_request)
            self.assertTrue(push_request.payment_created)
        else:
            push_request = PushRequest.objects.latest('id')
            self.assertIsNone(push_request.payment)
            self.assertFalse(push_request.payment_created)
        self.assertTrue(push_request.valid_checksum)
        self.client.logout()

    @requests_mock.mock()
    @patch('risk_management.task_summary.OrderCover.run')
    @patch('payments.views.get_client_ip')
    def test_release_fiat_order(self, mock, get_client_ip, cover_run):
        mock.get(
            settings.BINCODES_BANK_URL.format(
                bin=self.bankbins_resp['bin'],
                api_key=settings.BINCODES_API_KEY
            ),
            json=self.bankbins_resp
        )
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        # XVG is coverable
        order = self._create_order_api(
            pair_name='XVGEUR',
            address='D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'
        )

        before_kyc = self._create_kyc(order.unique_reference)
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='PENDING')
        url = reverse('payments.listen_safe_charge')
        cover_run.assert_not_called()
        res = self.client.post(url, data=params)
        # PushRequest called second time - it is not forbidden to do that and
        # SafeCharge is responsible for that - no us.
        self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        before_kyc.refresh_from_db()
        self.assertEqual(before_kyc.payment_preference,
                         payment.payment_preference)
        self._check_bank_bin(payment.payment_preference)
        # Create a VerificationCategory with this bank
        bank = payment.payment_preference.bank_bin.bank
        bank_cat = VerificationCategory.objects.create(name='Bank Cat')
        bank_cat.banks.add(bank)
        # Create Verification EQUAL category
        e_rule = CategoryRule.objects.create(
            key='bin', value=self.bankbins_resp['bin'],
            rule_type=CategoryRule.EQUAL
        )
        equal_categ = VerificationCategory.objects.create(name='Equal Categ')
        equal_categ.rules.add(e_rule)
        # Create Verification IN category
        i_rule = CategoryRule.objects.create(
            key='nameOnCard', value=name.upper(),
            rule_type=CategoryRule.IN
        )
        in_categ = VerificationCategory.objects.create(name='In Categ')
        in_categ.rules.add(i_rule)
        push_requests = PushRequest.objects.filter(payment=payment)
        self.assertEqual(push_requests.count(), 2)
        self.assertEqual(cover_run.call_count, 1)
        for push_request in push_requests:
            self.assertIn('safe_charge', push_request.url)
            self.assertIn('name', push_request.payload)
            self.assertTrue(push_request.valid_checksum)
        push_request1 = push_requests.get(payment_created=True)
        push_request2 = push_requests.get(payment_created=False)
        self.assertTrue(push_request1.created_on < push_request2.created_on)

        self.assertFalse(payment.is_complete)
        self.assertFalse(payment.is_success)

        # Check without KYC
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertFalse(self._check_kyc(order.unique_reference))
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        # Check with Pending KYC
        kyc = self._create_kyc(order.unique_reference)
        all_categs = kyc.category.all()
        self.assertIn(bank_cat, all_categs)
        self.assertIn(equal_categ, all_categs)
        self.assertIn(in_categ, all_categs)
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertFalse(self._check_kyc(order.unique_reference))
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        # Check with Confirmed KYC, but payment PENDING
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.save()
        # test KYC name checker
        with patch('verification.task_summary.send_email') as _send:
            kyc.flag(val='flag match names')
            check_kyc_names_periodic.apply_async()
            _send.assert_not_called()
            kyc.flagged = False
            kyc.save()
            check_kyc_names_periodic.apply_async()
            _send.assert_called_once()
            kyc.full_name = name
            kyc.save()
            check_kyc_names_periodic.apply_async()
            _send.assert_called_once()
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
        self.assertFalse(payment.is_complete)
        # Not set as paid if flagged KYC
        kyc.flag(val='flagg before release')
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        kyc.flagged = False
        kyc.save()
        #
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        payment.refresh_from_db()
        self.assertTrue(payment.is_complete)

        self._test_paid_order(order)

    @patch('payments.views.get_client_ip')
    def test_dont_set_as_paid_non_immiadiate(self, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(
            order, card_id, name,
            payment_method='some_method'
        )

        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)

        kyc = self._create_kyc(order.unique_reference)
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.save()
        self.assertTrue(self._check_kyc(order.unique_reference))
        self.assertTrue(self._check_kyc(order.unique_reference))
        payment = order.payment_set.get()
        self.assertTrue(payment.is_success)
        pref = payment.payment_preference
        self.assertTrue(pref.is_verified)
        self.assertFalse(pref.is_immediate_payment)

        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)

    @patch('payments.views.get_client_ip')
    @patch('payments.api_clients.safe_charge.SafeCharge.voidTransaction')
    def test_void_fiat_order(self, void_tx, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        void_tx.return_value = {'transactionStatus': 'APPROVED'}
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertTrue(payment.is_success)
        res = order.refund()
        self.assertEqual(res['status'], 'OK', res)
        self.assertEqual(order.status, Order.REFUNDED)
        payment.refresh_from_db()
        self.assertTrue(payment.flagged)
        order.refund()
        void_tx.assert_called_once()

    @patch('payments.views.get_client_ip')
    @patch('payments.api_clients.safe_charge.SafeCharge.voidTransaction')
    @patch('payments.api_clients.safe_charge.SafeCharge.refundTransaction')
    def test_void_fiat_order_with_task(self, refund_tx, void_tx,
                                       get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        void_tx.return_value = {'transactionStatus': 'APPROVED'}
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertTrue(payment.is_success)
        check_payments_for_void_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        now = datetime.datetime.now() + settings.KYC_WAIT_VOID_INTERVAL
        with freeze_time(now):
            self.assertTrue(payment.kyc_wait_void_period_expired)
            check_payments_for_void_periodic.apply_async()
            order.refresh_from_db()
            self.assertEqual(order.status, Order.REFUNDED)
        refund_tx.assert_not_called()
        void_tx.assert_called_once()

    @patch('payments.views.get_client_ip')
    @patch('payments.api_clients.safe_charge.SafeCharge.voidTransaction')
    @patch('payments.api_clients.safe_charge.SafeCharge.refundTransaction')
    def test_refund_fiat_order_with_task(self, refund_tx, void_tx,
                                         get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        refund_tx.return_value = {'transactionStatus': 'APPROVED'}
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertTrue(payment.is_success)
        check_payments_for_refund_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        now = datetime.datetime.now() + settings.KYC_WAIT_REFUND_INTERVAL
        with freeze_time(now):
            self.assertTrue(payment.kyc_wait_refund_period_expired)
            check_payments_for_refund_periodic.apply_async()
            order.refresh_from_db()
            self.assertEqual(order.status, Order.REFUNDED)
        refund_tx.assert_called_once()
        void_tx.assert_not_called()

    @patch('payments.views.get_client_ip')
    @patch('payments.api_clients.safe_charge.SafeCharge.voidTransaction')
    @patch('payments.api_clients.safe_charge.SafeCharge.refundTransaction')
    def test_do_not_auto_refund_fiat_order_with_verification(self, refund_tx,
                                                             void_tx,
                                                             get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        self._create_kyc(order.unique_reference)

        now = datetime.datetime.now() + settings.KYC_WAIT_REFUND_INTERVAL
        with freeze_time(now):
            self.assertFalse(payment.kyc_wait_refund_period_expired)
            check_payments_for_refund_periodic.apply_async()
            order.refresh_from_db()
            self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        refund_tx.assert_not_called()
        void_tx.assert_not_called()

    @patch('payments.views.get_client_ip')
    @patch('payments.api_clients.safe_charge.SafeCharge.voidTransaction')
    @patch('payments.api_clients.safe_charge.SafeCharge.refundTransaction')
    def test_do_not_auto_void_fiat_order_with_verification(self, refund_tx,
                                                           void_tx,
                                                           get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.get()
        self.assertFalse(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        self._create_kyc(order.unique_reference)

        now = datetime.datetime.now() + settings.KYC_WAIT_VOID_INTERVAL
        with freeze_time(now):
            self.assertFalse(payment.kyc_wait_void_period_expired)
            check_payments_for_void_periodic.apply_async()
            order.refresh_from_db()
            self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        refund_tx.assert_not_called()
        void_tx.assert_not_called()

    @data_provider(lambda: (
        do_not_refund_fiat_order_params(
            case_name='Non successful payment from the customer',
            payment_data={'is_success': False},
            tx_status='APPROVED',
            order_status=None
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order id on payment',
            payment_data={'order_id': 1},
            tx_status='APPROVED',
            order_status=None
        ),
        do_not_refund_fiat_order_params(
            case_name='Error on refund call',
            payment_data={},
            tx_status='ERROR',
            order_status=None
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - INITIAL',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.INITIAL
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - PAID',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.PAID
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - CANCELED',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.CANCELED
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - PRE_RELEASE',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.PRE_RELEASE
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - RELEASED',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.RELEASED
        ),
        do_not_refund_fiat_order_params(
            case_name='Bad order status - COMPLETED',
            payment_data={},
            tx_status='APPROVED',
            order_status=Order.COMPLETED
        ),
    ))
    @patch('payments.views.get_client_ip')
    @patch('orders.models.Order._validate_status')
    @patch('payments.api_clients.safe_charge.SafeCharge.refundTransaction')
    def test_do_not_refund_fiat_order(self, refund_tx, validate_status,
                                      get_client_ip, **kwargs):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        tx_status = kwargs['tx_status']
        order_status = kwargs['order_status']
        case_name = kwargs['case_name']
        payment_data = kwargs['payment_data']
        validate_status.return_value = True
        refund_tx.return_value = {'transactionStatus': tx_status}
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200, case_name)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED, case_name)
        if order_status is not None:
            order.status = order_status
            order.save()
            order.refresh_from_db()
            self.assertEqual(order.status, order_status, case_name)
        payment = order.payment_set.get()
        for key, value in payment_data.items():
            setattr(payment, key, value)
        payment.save()
        before_status = order.status
        res = order.refund()
        order.refresh_from_db()
        self.assertEqual(order.status, before_status, case_name)
        self.assertEqual(res['status'], 'ERROR',
                         '{}, {}'.format(res, case_name))
        self.assertEqual(order.status, before_status, case_name)

    @patch('payments.views.get_client_ip')
    def test_try_release_fiat_with_corrupted_signature_push(self,
                                                            get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')
        params['advancedResponseChecksum'] += 's'

        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.INITIAL)
        with self.assertRaises(Payment.DoesNotExist):
            order.payment_set.get()
        push_request = PushRequest.objects.latest('id')
        self.assertFalse(push_request.valid_checksum)
        self.assertTrue(push_request.valid_timestamp)
        self.assertTrue(push_request.valid_ip)
        self.assertFalse(push_request.payment_created)

    @patch('payments.views.get_client_ip')
    def test_try_release_fiat_with_bad_response_time(self, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(
            order, card_id, name, status='APPROVED',
            time_stamp='2017-12-12.05:05:05')
        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.INITIAL)
        with self.assertRaises(Payment.DoesNotExist):
            order.payment_set.get()
        push_request = PushRequest.objects.latest('id')
        self.assertTrue(push_request.valid_checksum)
        self.assertTrue(push_request.valid_ip)
        self.assertFalse(push_request.valid_timestamp)
        self.assertFalse(push_request.payment_created)

    @patch('payments.views.get_client_ip')
    def test_try_release_fiat_with_bad_ip(self, get_client_ip):
        get_client_ip.return_value = '0.0.0.0'
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(
            order, card_id, name, status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.INITIAL)
        with self.assertRaises(Payment.DoesNotExist):
            order.payment_set.get()
        push_request = PushRequest.objects.latest('id')
        self.assertTrue(push_request.valid_checksum)
        self.assertFalse(push_request.valid_ip)
        self.assertTrue(push_request.valid_timestamp)
        self.assertFalse(push_request.payment_created)

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
        # Allow inacuracy due to limited decimal places
        self.assertTrue(
            abs((expected_ticker_amount_quote - order.ticker_amount_quote) /
                expected_ticker_amount_quote) < Decimal('0.0001'))
        self.assertEqual(order.amount_quote, Decimal(amount_quote))
        self.assertAlmostEqual(order.amount_base, amount_base, 3)

    @patch('payments.views.get_client_ip')
    def test_set_verification_tiers(self, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        tier0 = VerificationTier.objects.get(name='Tier 0')
        tier1 = VerificationTier.objects.get(name='Tier 1')
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name)

        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        kyc = self._create_kyc(order.unique_reference)
        pref = kyc.payment_preference
        # Check with Confirmed KYC, but payment PENDING
        self.assertEqual(pref.tier, tier0)
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.save()
        pref.refresh_from_db()
        self.assertEqual(pref.tier, tier1)

    @patch('payments.views.get_client_ip')
    def test_do_not_set_as_paid_order_out_of_daily_limit(self, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        tier1 = VerificationTier.objects.get(name='Tier 1')
        trade_limit = tier1.trade_limits.get(days=1)
        other_limits = tier1.trade_limits.exclude(pk=trade_limit.pk)
        for limit in other_limits:
            limit.amount = trade_limit.amount * Decimal(100)
            limit.save()

        order_data = {
            'amount_quote': trade_limit.amount * Decimal(0.9),
            'pair': {
                'name': 'BTC{}'.format(trade_limit.currency.code)
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }

        # Create first Order
        order1 = self._create_order_api(order_data=order_data)
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order1, card_id, name)

        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        kyc = self._create_kyc(order1.unique_reference)
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.full_name = name
        kyc.save()
        check_fiat_order_deposit_periodic.apply_async()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.PAID)
        # Create second order (over the daily limit)
        order2 = self._create_order_api(order_data=order_data)
        params = self._get_dmn_request_params_for_order(order2, card_id, name)
        self.client.post(url, data=params)
        order2.refresh_from_db()
        self.assertEqual(order1.payment_set.get().payment_preference,
                         order2.payment_set.get().payment_preference)
        check_fiat_order_deposit_periodic.apply_async()
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.PAID_UNCONFIRMED)

        now = datetime.datetime.now() + datetime.timedelta(days=1, seconds=1)
        with freeze_time(now):
            check_fiat_order_deposit_periodic.apply_async()
            order2.refresh_from_db()
            self.assertEqual(order2.status, Order.PAID)

    @patch('payments.views.get_client_ip')
    def test_do_not_set_as_paid_order_out_of_monthly_limit(self,
                                                           get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        tier1 = VerificationTier.objects.get(name='Tier 1')
        daily_limit = tier1.trade_limits.get(days=1)
        monthly_limit = tier1.trade_limits.get(days=30)
        # Set monthly as double daily limit
        monthly_limit.amount = daily_limit.amount * Decimal('2')
        monthly_limit.currency = daily_limit.currency
        monthly_limit.save()

        order_data = {
            'amount_quote': daily_limit.amount * Decimal(0.9),
            'pair': {
                'name': 'BTC{}'.format(monthly_limit.currency.code)
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }

        # Create first order
        order1 = self._create_order_api(order_data=order_data)
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order1, card_id, name)

        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        kyc = self._create_kyc(order1.unique_reference)
        kyc.util_status = kyc.OK
        kyc.id_status = kyc.OK
        kyc.full_name = name
        kyc.save()
        check_fiat_order_deposit_periodic.apply_async()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.PAID)
        # Create second order. After 1 day - both monthly and daily limits
        # should pass
        order2 = self._create_order_api(order_data=order_data)
        params = self._get_dmn_request_params_for_order(order2, card_id, name)
        self.client.post(url, data=params)

        now = datetime.datetime.now() + datetime.timedelta(days=1, seconds=1)
        with freeze_time(now):
            check_fiat_order_deposit_periodic.apply_async()
            order2.refresh_from_db()
            self.assertEqual(order2.status, Order.PAID)
        # Create Third order. After 2 day - both monthly and daily limits
        # should pass
        order3 = self._create_order_api(order_data=order_data)
        params = self._get_dmn_request_params_for_order(order3, card_id, name)
        self.client.post(url, data=params)

        now = datetime.datetime.now() + datetime.timedelta(days=2, seconds=1)
        with freeze_time(now):
            check_fiat_order_deposit_periodic.apply_async()
            order3.refresh_from_db()
            self.assertEqual(order3.status, Order.PAID_UNCONFIRMED)
        now = datetime.datetime.now() + datetime.timedelta(days=30, seconds=1)
        with freeze_time(now):
            check_fiat_order_deposit_periodic.apply_async()
            order3.refresh_from_db()
            self.assertEqual(order3.status, Order.PAID)

    @patch('payments.views.get_client_ip')
    @patch('payments.models.send_email')
    def test_approve_documents_and_check_tier(self, mock_send_email,
                                              get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api(
            pair_name='XVGEUR',
            address='D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'
        )
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name,
                                                        status='APPROVED')

        url = reverse('payments.listen_safe_charge')
        res = self.client.post(url, data=params)
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        pref = order.payment_set.get().payment_preference
        self.assertFalse(pref.is_verified)
        self.assertEqual(pref.tier.level, 0)
        # Upload kyc
        kyc = self._create_kyc(order.unique_reference)
        user = kyc.user
        user.email = 'example@mail.com'
        user.save()
        docs = kyc.verificationdocument_set.all()
        id_doc = docs.get(document_type__name='ID')
        util_doc = docs.get(document_type__name='UTIL')
        selfie = docs.get(document_type__name='SELFIE')
        whitelist_selfie = docs.get(document_type__name='WHITELIST_SELFIE')
        # id OK, util PENDING, selfie PENDING
        id_doc.document_status = id_doc.OK
        id_doc.save()
        pref.refresh_from_db()
        self.assertFalse(pref.is_verified)
        self.assertEqual(pref.tier.level, 0)
        # id OK, util OK, selfie PENDING
        util_doc.document_status = id_doc.OK
        util_doc.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 1)
        self.assertEqual(mock_send_email.call_count, 1)
        # id OK, util OK, selfie OK
        selfie.document_status = id_doc.OK
        selfie.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 2)
        self.assertEqual(mock_send_email.call_count, 2)
        # id OK, util OK, selfie OK, whitelist_selfie OK
        self.assertNotIn(order.withdraw_address, pref.whitelisted_addresses)
        whitelist_selfie.document_status = id_doc.OK
        whitelist_selfie.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 3)
        self.assertEqual(mock_send_email.call_count, 3)
        self.assertEqual(whitelist_selfie.whitelisted_address,
                         order.withdraw_address)
        self.assertIn(order.withdraw_address, pref.whitelisted_addresses)

    def test_create_on_verification_per_order(self):
        order = self._create_order_api(
            pair_name='XVGEUR',
            address='D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'
        )
        kyc1 = self._create_kyc(order.unique_reference)
        kyc2 = self._create_kyc(order.unique_reference)
        self.assertEqual(kyc1, kyc2)

    @patch('risk_management.task_summary.OrderCover.run')
    @patch('payments.views.get_client_ip')
    def test_release_whitelisted_order(self, get_client_ip, cover_run):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        # XVG is coverable
        whitelisted_order = self._create_order_api(
            pair_name='XVGEUR',
            address='D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'
        )
        other_order = self._create_order_api(
            pair_name='XVGEUR',
            address='DRVpPLkb1Vvxk7FY4RejcTFVDiR2eWznRW'
        )
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        white_params = self._get_dmn_request_params_for_order(
            whitelisted_order, card_id, name, status='APPROVED')
        other_params = self._get_dmn_request_params_for_order(
            other_order, card_id, name, status='APPROVED')
        url = reverse('payments.listen_safe_charge')
        for params in [white_params, other_params]:
            res = self.client.post(url, data=params)
            self.assertEqual(res.status_code, 200)
        for order in [whitelisted_order, other_order]:
            order.refresh_from_db()
            self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        pref = whitelisted_order.payment_set.get().payment_preference
        # Approve all documents of the first order
        kyc = self._create_kyc(whitelisted_order.unique_reference)
        kyc.full_name = name
        kyc.save()
        docs = kyc.verificationdocument_set.all()
        for doc in docs:
            doc.document_status = kyc.OK
            doc.save()
        # make preference out of limit
        pref.refresh_from_db()
        trade_limits = pref.tier.trade_limits.all()
        for _limit in trade_limits:
            # make limit less than order amount(preference - out of limit)
            _limit.amount = order.amount_quote * Decimal('0.9')
            _limit.save()
        # Run task
        check_fiat_order_deposit_periodic.apply_async()
        # Check statuses (first order must be PAID second not - because
        # address is not in whitelist
        self.assertIn(whitelisted_order.withdraw_address,
                      pref.whitelisted_addresses)
        whitelisted_order.refresh_from_db()
        self.assertEqual(whitelisted_order.status, Order.PAID)
        self.assertNotIn(other_order.withdraw_address,
                         pref.whitelisted_addresses)
        order.refresh_from_db()
        self.assertEqual(other_order.status, Order.PAID_UNCONFIRMED)
        # White list other order
        other_kyc = self._create_kyc(other_order.unique_reference)
        other_kyc.full_name = name
        other_kyc.save()
        whitelist_selfie = other_kyc.verificationdocument_set.get(
            document_type__name='WHITELIST_SELFIE'
        )
        whitelist_selfie.document_status = kyc.OK
        whitelist_selfie.save()
        self.assertIn(other_order.withdraw_address,
                      pref.whitelisted_addresses)
        # Run task again
        check_fiat_order_deposit_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(other_order.status, Order.PAID)

    @requests_mock.mock()
    @patch('payments.views.get_client_ip')
    def test_upload_id_from_idenfy(self, mock, get_client_ip):
        token = 'I+AM_A-rndmtken'
        scan_ref = 'ami_mucjhyreferenc'
        first_name = 'Sir'
        last_name = 'Testalot'
        full_name = '{} {}'.format(first_name, last_name)
        file_url = 'https://ivs.idenfy.com/storage/get/jwt_tkn/BACK.jpg'
        birth_date = '1990-01-01'
        exp_date = '2099-01-01'
        country_code = 'SS'
        mock.get(file_url, status_code=200)

        def token_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params['firstName'] == first_name and params['lastName'] == last_name:  # noqa
                return {'authToken': token,
                        'scanRef': scan_ref
                        }

        mock.post(
            settings.IDENFY_URL.format(
                endpoint='token',
                version=settings.IDENFY_VERSION
            ),
            json=token_callback,
            status_code=201
        )
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        # XVG is coverable
        order = self._create_order_api(
            pair_name='XVGEUR',
            address='D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'
        )
        # No link before
        self.assertIsNone(order.identity_check_url)
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id, name)
        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        order.refresh_from_db()
        self.assertEqual(order.identitytoken_set.count(), 0)
        self.assertIn('idenfy.com', order.identity_check_url)
        self.assertIn(token, order.identity_check_url)
        self.assertEqual(order.identity_token, token)
        self.assertEqual(order.identitytoken_set.count(), 1)
        first_token = order.identitytoken_set.get()
        self.assertEqual(first_token.first_name, first_name)
        self.assertEqual(first_token.last_name, last_name)
        now = datetime.datetime.now() + datetime.timedelta(
            seconds=settings.IDENFY_TOKEN_EXPIRY_TIME
        )
        with freeze_time(now):
            mock.post(
                settings.IDENFY_URL.format(
                    endpoint='token',
                    version=settings.IDENFY_VERSION
                ),
                json={'authToken': 'asd', 'scanRef': 'asd'},
                status_code=201
            )
            order.identity_token
            self.assertEqual(order.identitytoken_set.count(), 2)
        url_idenfy_callback = reverse('verification.idenfy_callback')
        # First time unsuccsesfull
        callback_data = {
            'clientId': order.unique_reference,
            'scanRef': scan_ref,
            'idLastName': last_name,
            'idFirstName': first_name,
            'identificationStatus': 'FACE_MISMATCH',
            'fileUrls': {
                'BACK': file_url,
            }
        }
        res = self.client.post(
            url_idenfy_callback,
            content_type='application/json',
            data=json.dumps(callback_data),
        )
        self.assertEqual(res.status_code, 200)
        kyc = Verification.objects.get(note=order.unique_reference)
        doc = kyc.verificationdocument_set.latest('id')
        kyc_push = doc.kyc_push
        self.assertIsNone(kyc.full_name)
        self.assertEqual(doc.document_status, doc.REJECTED)
        self.assertFalse(kyc_push.identification_approved)
        self.assertEqual(kyc_push.full_name, full_name)
        self.assertEqual(kyc_push.token, first_token)
        # Second time OK
        callback_data.update({
            'identificationStatus': 'APPROVED',
            'idDob': birth_date,
            'idExpiry': exp_date,
            'data': {
                'docNationality': country_code,
                'selectedCountry': country_code,
                'docIssuingCountry': country_code,
            }
        })
        res = self.client.post(
            url_idenfy_callback,
            content_type='application/json',
            data=json.dumps(callback_data),
        )
        id_token = order.identitytoken_set.latest('id')
        self.assertTrue(id_token.used)
        self.assertEqual(res.status_code, 200)
        kyc = Verification.objects.get(note=order.unique_reference)
        doc = kyc.verificationdocument_set.latest('id')
        kyc_push = doc.kyc_push
        self.assertEqual(kyc.full_name, full_name)
        self.assertEqual(doc.document_status, doc.OK)
        self.assertTrue(kyc_push.identification_approved)
        self.assertEqual(kyc_push.full_name, full_name)
        self.assertEqual(kyc_push.nationality.country.code, country_code)
        self.assertEqual(kyc_push.issuing_country.country.code, country_code)
        self.assertEqual(kyc_push.selected_country.country.code, country_code)
        self.assertEqual(str(kyc_push.birth_date), birth_date)
        self.assertEqual(str(kyc_push.doc_expiration), exp_date)
