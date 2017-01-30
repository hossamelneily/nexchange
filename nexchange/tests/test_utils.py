from unittest import TestCase
from nexchange.utils import PayeerAPIClient, check_address_blockchain
import requests_mock
from core.models import Address
from core.tests.base import UserBaseTestCase, OrderBaseTestCase


class PayeerAPIClientTestCase(TestCase):

    def setUp(self):
        self.url = 'https://payeer.com/ajax/api/api.php'
        self.client = PayeerAPIClient(url=self.url)

    @requests_mock.mock()
    def test_history_of_transactions(self, m):
        cont_path = 'nexchange/tests/fixtures/payeer/transaction_history.json'
        with open(cont_path) as f:
            m.post(self.url, text=f.read().replace('\n', ''))
        res = self.client.history_of_transactions()
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


class BlockchainTestCase(UserBaseTestCase, OrderBaseTestCase):

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
        cont_path = 'nexchange/tests/fixtures/blockr/address_transactions.json'
        with open(cont_path) as f:
            m.get(self.url, text=f.read().replace('\n', ''))
        res = check_address_blockchain(self.address)
        self.assertEqual(2, len(res))
