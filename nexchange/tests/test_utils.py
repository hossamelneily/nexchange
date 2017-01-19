from unittest import TestCase
from nexchange.utils import PayeerAPIClient


class PayeerAPIClientTestCase(TestCase):

    def setUp(self):
        self.client = PayeerAPIClient()

    def test_authorization_check(self):
        res = self.client.authorization_check()
        self.assertEqual(res.status_code, 200)

    def test_history_of_transactions(self):
        res = self.client.history_of_transactions()
        self.assertEqual(res.status_code, 200)
