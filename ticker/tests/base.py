import json

from core.tests.base import OrderBaseTestCase
from ticker.tasks.generic.base import BaseTicker
from ticker.task_summary import get_all_tickers
import requests_mock


class TickerBaseTestCase(OrderBaseTestCase):

    def setUp(self):
        super(TickerBaseTestCase, self).setUp()
        self._read_fixtures_ticker()
        with requests_mock.mock() as mock:
            self.get_tickers(mock)

    def _read_fixtures_ticker(self):
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
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_SELL),
                 text=self.localbtc_sell_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_BUY),
                 text=self.localbtc_sell_resp)

    def get_tickers(self, mock):
        self.mock_resources(mock)
        get_all_tickers.apply()
