from unittest import TestCase
from unittest.mock import patch
from decimal import Decimal
from nexchange.utils import check_address_blockchain, AESCipher, ip_in_iplist
from payments.api_clients.ok_pay import OkPayAPI
from payments.api_clients.payeer import PayeerAPIClient
import requests_mock
from core.models import Address
from core.tests.base import OrderBaseTestCase
from core.tests.utils import get_ok_pay_mock, get_payeer_mock
from django.conf import settings
import os
from core.tests.utils import retry


class PayeerAPIClientTestCase(TestCase):

    def setUp(self):
        self.url = 'https://payeer.com/ajax/api/api.php'
        self.client = PayeerAPIClient(url=self.url)

    @requests_mock.mock()
    def test_history_of_transactions(self, m):
        m.post(self.url, text=get_payeer_mock('transaction_history'))
        res = self.client.get_transaction_history()
        key = next(iter(res))
        self.assertIn('id', res[key])
        self.assertEqual(res[key]['id'], key)
        self.assertIn('type', res[key])
        self.assertIn('status', res[key])
        self.assertIn('from', res[key])
        self.assertIn('creditedCurrency', res[key])
        self.assertIn('to', res[key])
        self.assertIn('shopOrderId', res[key])
        self.assertIn('shopId', res[key])
        self.assertIn('comment', res[key])

    @requests_mock.mock()
    def test_transfer_funds(self, m):
        m.post(self.url, text=get_payeer_mock('transfer_funds'))
        res = self.client.transfer_funds(
            currency_in='EUR', currency_out='EUR', amount=Decimal('0.02'),
            receiver='WEARE@ONIT.WS'
        )
        self.assertFalse(res['errors'])

    @requests_mock.mock()
    def test_transfer_funds_balance_error(self, m):
        m.post(self.url, text=get_payeer_mock(
            'transfer_funds_balance_error'
        ))
        res = self.client.transfer_funds(
            currency_in='EUR', currency_out='EUR', amount=Decimal('0.02'),
            receiver='WEARE@ONIT.WS'
        )
        self.assertEqual(res['errors'][0], 'balanceError')


class OkPayAPIClientTestCase(TestCase):

    def setUp(self):
        self.client = OkPayAPI(
            api_password='password', wallet_id='OK*********'
        )

    def _ok_personal_keys(self, sender_receiver):
        expected_keys = [
            'AccountID', 'Country_ISO', 'Email', 'Name', 'VerificationStatus',
            'WalletID'
        ]
        for key in expected_keys:
            self.assertIn(key, sender_receiver)

    @patch('payments.api_clients.ok_pay.OkPayAPI._send_money')
    def test_send_money_keys(self, send_money):
        send_money.return_value = get_ok_pay_mock(
            data='transaction_send_money'
        )
        resp = self.client.send_money()
        expected_keys = [
            'Receiver', 'Sender', 'Amount', 'Comment', 'Currency', 'Date',
            'Fees', 'ID', 'Invoice', 'Net'
        ]
        for key in expected_keys:
            self.assertIn(key, resp)
        self._ok_personal_keys(resp['Sender'])
        self._ok_personal_keys(resp['Receiver'])


class BlockchainTestCase(OrderBaseTestCase):

    def setUp(self):
        super(BlockchainTestCase, self).setUp()
        self.wallet_address = '198aMn6ZYAczwrE5NvNTUMyJ5qkfy4g3Hi'
        self.address = Address(
            name='test address',
            address=self.wallet_address,
            currency=self.BTC,
            user=self.user
        )
        self.url = 'http://btc.blockr.io/api/v1/address/txs/{}'.format(
            self.wallet_address
        )

    @requests_mock.mock()
    def test_get_transactions_by_address(self, m):
        cont_path = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/blockr/address_transactions.json')
        with open(cont_path) as f:
            m.get(self.url, text=f.read().replace('\n', ''))
        res = check_address_blockchain(self.address)
        self.assertEqual(2, len(res['txs']))


class TestAesCypher(TestCase):
    @retry(UnicodeDecodeError, tries=3, delay=1)
    def test_decrypt_success(self):
        key = 'my_key'
        raw = 'my_secret'

        cipher = AESCipher(key)

        encrypted = cipher.encrypt(raw)
        decrypted = cipher.decrypt(encrypted)
        self.assertEqual(raw, decrypted)

    @retry(UnicodeDecodeError, tries=3, delay=1)
    def test_decrypt_failure(self):
        key = 'my_key'
        wrong_key = 'false_key'
        raw = 'my_secret'

        cipher = AESCipher(key)
        wrong_cipher = AESCipher(wrong_key)

        encrypted = cipher.encrypt(raw)
        decrypted = wrong_cipher.decrypt(encrypted)
        self.assertNotEqual(raw, decrypted)


class IpListTestCase(TestCase):

    def test_ip_iplist(self):
        ip_list = [
            '194.247.166.0-194.247.167.255',
            '0.0.0.0'
        ]
        ip_exact = '0.0.0.0'
        self.assertTrue(ip_in_iplist(ip_exact, ip_list))
        ip_in_range = '194.247.166.15'
        self.assertTrue(ip_in_iplist(ip_in_range, ip_list))
        ip_out_of_range = '194.247.165.255'
        self.assertFalse(ip_in_iplist(ip_out_of_range, ip_list))
