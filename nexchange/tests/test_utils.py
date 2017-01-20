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
        self.assertIn('id', res[0])
        self.assertIn('type', res[0])
        self.assertIn('status', res[0])
        self.assertIn('from', res[0])
        self.assertIn('creditedCurrency', res[0])
        self.assertIn('to', res[0])
        self.assertIn('shopOrderId', res[0])
        self.assertIn('shopId', res[0])
        self.assertIn('comment', res[0])
