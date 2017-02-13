from decimal import Decimal
from unittest.mock import patch
from unittest import skip

from django.test import TestCase
from django.utils.dateformat import format

from ticker.models import Price


class PriceTestCase(TestCase):

    @skip('Invalid, ticker structure changed')
    @patch('ticker.models.Price.get_ticker_crypto')
    def setUp(self, ticker):
        ticker.return_value = True
        self.price_usd = Decimal(650.88846)
        self.price_rub = Decimal(41758.2)
        self.data = {
            'better_adds_count': 1,
            'price_rub': self.price_rub,
            'price_usd': self.price_usd,
            'type': Price.BUY
        }

        self.price = Price(**self.data)
        self.price.save()

    @skip('Invalid, ticker structure changed')
    def test_returns_unix_time(self):
        self.assertEqual(self.price.unix_time,
                         format(self.price.created_on, 'U'))

    @skip('Invalid, ticker structure changed')
    def test_returns_price_in_usd(self):
        self.assertEqual(self.price.price_usd_formatted, self.price_usd)

    @skip('Invalid, ticker structure changed')
    def test_returns_price_in_rub(self):
        self.assertEqual(self.price.price_rub_formatted, self.price_rub)
