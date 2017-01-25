from unittest import TestCase
from nexchange.utils import PayeerAPIClient
import requests_mock


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
