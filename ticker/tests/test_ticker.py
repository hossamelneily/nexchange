from ticker.models import Price
import requests_mock
import json
from decimal import Decimal
from unittest import skip

from core.tests.base import OrderBaseTestCase
from core.models import Currency
from ticker.tasks.generic.base import BaseTicker


class TestTicker(OrderBaseTestCase):

    def setUp(self):
        super(TestTicker, self).setUp()
        self.data = {
            'price_rub': 60000,
            'price_usd': 1000
        }
        self.url = BaseTicker.KRAKEN_RESOURCE
        self.url_fixer = BaseTicker.EUR_RESOURCE
        self._read_fixtures()

    def _read_fixtures(self):
        kraken_path = 'ticker/tests/fixtures/kraken_ticker.json'
        fixer_path = 'ticker/tests/fixtures/fixer.json'
        with open(kraken_path) as f:
            self.kraken_resp = f.read().replace('\n', '')
        self.kraken_info = json.loads(self.kraken_resp)['result']
        with open(fixer_path) as f:
            self.fixer_resp = f.read().replace('\n', '')

    @skip('Invalid, ticker structure changed')
    @requests_mock.mock()
    def test_ticker_ask_bid(self, m):
        m.get(self.url, text=self.kraken_resp)
        m.get(self.url_fixer, text=self.fixer_resp)
        price = Price(**self.data)
        price.save()
        # expected
        expected_eth_ask = Decimal('1.0') / Decimal(
            self.kraken_info['XETHXXBT']['b'][0])
        expected_eth_bid = Decimal('1.0') / Decimal(
            self.kraken_info['XETHXXBT']['a'][0])
        expected_ltc_ask = Decimal('1.0') / Decimal(
            self.kraken_info['XLTCXXBT']['b'][0])
        expected_ltc_bid = Decimal('1.0') / Decimal(
            self.kraken_info['XLTCXXBT']['a'][0]
        )

        # test
        self.assertEqual(price.ticker_eth.ask, expected_eth_ask)
        self.assertEqual(price.ticker_eth.bid, expected_eth_bid)
        self.assertEqual(price.ticker_ltc.ask, expected_ltc_ask)
        self.assertEqual(price.ticker_ltc.bid, expected_ltc_bid)

    @skip('Invalid, ticker structure changed')
    @requests_mock.mock()
    def test_ticker_currencies(self, m):
        m.get(self.url, text=self.kraken_resp)
        m.get(self.url_fixer, text=self.fixer_resp)
        price = Price(**self.data)
        price.save()
        LTC = Currency.objects.get(code='LTC')
        ETH = Currency.objects.get(code='ETH')

        # test
        self.assertEqual(price.ticker_eth.quote, ETH)
        self.assertEqual(price.ticker_ltc.quote, LTC)
        self.assertEqual(price.ticker_eth.base, self.BTC)
        self.assertEqual(price.ticker_ltc.base, self.BTC)
