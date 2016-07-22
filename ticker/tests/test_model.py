from django.utils.dateformat import format
from django.test import TestCase
from datetime import datetime

from ticker.models import Price


class PriceTestCase(TestCase):

    def setUp(self):

        self.created_on = datetime.now()
        self.data = {
            'better_adds_count': 1,
            'price_rub': 41758.2,
            'price_usd': 650.88846,
            'rate': 64.15569266660528,
            'type': 'B',
            'created_on': self.created_on
        }

        self.price = Price(**self.data)
        self.price.save()

    def test_returns_unix_time(self):
        self.assertEqual(self.price.unix_time, format(self.created_on, 'U'))

    def test_returns_price_in_usd(self):
        self.assertEqual(self.price.price_usd_formatted, 650.89)

    def test_returns_price_in_rubd(self):
        self.assertEqual(self.price.price_rub_formatted, 41758.2)
