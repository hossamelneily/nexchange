from ticker.models import Price
import requests_mock
import json

from core.tests.base import OrderBaseTestCase
from ticker.tasks.generic.base import BaseTicker
from ticker.task_summary import get_all_tickers


class TestTickerTask(OrderBaseTestCase):

    def setUp(self):
        super(TestTickerTask, self).setUp()
        self.main_ticker = self.BTCEUR
        self.main_ticker.disabled = False
        self.main_ticker.save()
        self.disabled_ticker = self.BTCUSD
        self.disabled_ticker.disabled = True
        self.disabled_ticker.save()
        self._read_fixtures()

    def _read_fixtures(self):
        kraken_path = 'ticker/tests/fixtures/kraken_ticker.json'
        fixer_path = 'ticker/tests/fixtures/fixer.json'
        bitifex_path = 'ticker/tests/fixtures/bitifex.json'
        localbtc_buy_path = 'ticker/tests/fixtures/localbtc/buy.json'
        localbtc_sell_path = 'ticker/tests/fixtures/localbtc/sell.json'
        with open(kraken_path) as f:
            self.kraken_resp = f.read().replace('\n', '')
        self.kraken_info = json.loads(self.kraken_resp)['result']
        with open(fixer_path) as f:
            self.fixer_resp = f.read().replace('\n', '')
        with open(bitifex_path) as f:
            self.bitifex_resp = f.read().replace('\n', '')
        with open(localbtc_buy_path) as f:
            self.localbtc_buy_resp = f.read().replace('\n', '')
        with open(localbtc_sell_path) as f:
            self.localbtc_sell_resp = f.read().replace('\n', '')

    def mock_resources(self, mock):
        mock.get(BaseTicker.KRAKEN_RESOURCE, text=self.kraken_resp)
        mock.get(BaseTicker.BITFINEX_TICKER, text=self.bitifex_resp)
        mock.get(BaseTicker.EUR_RESOURCE, text=self.fixer_resp)
        mock.get(BaseTicker.EUR_RESOURCE, text=self.fixer_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_SELL),
                 text=self.localbtc_sell_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_BUY),
                 text=self.localbtc_sell_resp)

    @requests_mock.mock()
    def test_create_enabled_ticker(self, m):
        self.mock_resources(m)
        before = len(Price.objects.filter(pair=self.main_ticker))
        get_all_tickers.apply()
        after = len(Price.objects.filter(pair=self.main_ticker))
        self.assertEqual(before + 1, after)

    @requests_mock.mock()
    def test_do_not_create_disabled_ticker(self, m):
        self.mock_resources(m)
        before = len(Price.objects.filter(pair=self.disabled_ticker))
        get_all_tickers.apply()
        after = len(Price.objects.filter(pair=self.disabled_ticker))
        self.assertEqual(before, after)
