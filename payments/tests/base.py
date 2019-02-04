from unittest.mock import patch

from core.models import Currency
from core.tests.base import VerificationBaseTestCase
from core.tests.base import SCRYPT_ROOT
from orders.models import Order
from orders.task_summary import buy_order_release_reference_periodic
from payments.models import Payment, PaymentPreference
from payments.payment_handlers.safe_charge import SafeChargePaymentHandler
from rest_framework.test import APIClient
import json
from verification.models import Verification, VerificationDocument
from ticker.tests.base import TickerBaseTestCase

from PIL import Image
import tempfile


class BaseFiatOrderTestCase(TickerBaseTestCase, VerificationBaseTestCase):

    def setUp(self, *args, **kwargs):
        super(BaseFiatOrderTestCase, self).setUp(*args, **kwargs)
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

    def tearDown(self, *args, **kwargs):
        VerificationDocument.objects.all().delete()
        super(BaseFiatOrderTestCase, self).tearDown(*args, **kwargs)

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

    @patch(SCRYPT_ROOT + '_list_txs')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch('orders.models.Order.coverable')
    def _test_paid_order(self, order, coverable, scrypt_info, scrypt_list_txs):
        scrypt_list_txs.return_value = []
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
