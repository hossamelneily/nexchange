import json

from core.tests.base import OrderBaseTestCase
from ticker.tasks.generic.base import BaseTicker
from ticker.task_summary import get_all_tickers
from ticker.adapters import KrakenAdapter, CryptopiaAdapter, \
    CoinexchangeAdapter
from ticker.tests.fixtures.coinexchange.markets import \
    response as coinex_markets_resp
from ticker.tests.fixtures.coinexchange.market_summary import \
    response as coinex_market_summary_resp
import requests_mock
from core.models import Pair
from ticker.tests.fixtures.cryptopia_ticker import res as \
    cryptopia_ticker_resp_empty


class TickerBaseTestCase(OrderBaseTestCase):

    def setUp(self):
        super(TickerBaseTestCase, self).setUp()
        self._read_fixtures_ticker()
        with requests_mock.mock() as mock:
            self.get_tickers(mock)

    def _read_fixtures_ticker(self):
        cryptopia_markets_path = 'ticker/tests/fixtures/cryptopia_markets.json'
        kraken_ticker_path = 'ticker/tests/fixtures/kraken_ticker.json'
        fixer_path = 'ticker/tests/fixtures/fixer.json'
        bitifex_path = 'ticker/tests/fixtures/bitifex.json'
        localbtc_buy_path = 'ticker/tests/fixtures/localbtc/buy.json'
        localbtc_sell_path = 'ticker/tests/fixtures/localbtc/sell.json'
        with open(cryptopia_markets_path) as f:
            self.cryptopia_markets_resp = f.read().replace('\n', '')
        self.cryptopia_ticker_resp = cryptopia_ticker_resp_empty
        with open(kraken_ticker_path) as f:
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

    def cryptopia_market_mapper(self, pair):
        mapper = {
            'XVG/BTC': 1376,
            'DOGE/BTC': 102,
            'XVG/DOGE': 1378
        }
        return mapper[pair]

    def mock_resources(self, mock):
        mock.get(
            CryptopiaAdapter.RESOURCE_MARKETS,
            text=self.cryptopia_markets_resp)

        cryptopia_pairs = Pair.objects.filter(quote__code__in=['XVG', 'DOGE'],
                                              base__code__in=['BTC', 'DOGE'])
        for pair in cryptopia_pairs:
            pair_name = '{}/{}'.format(pair.quote.code, pair.base.code)
            market_id = self.cryptopia_market_mapper(pair_name)
            url = CryptopiaAdapter.RESOURCE_TICKER_PARAM.format(market_id)
            mock.get(
                url,
                text=self.cryptopia_ticker_resp.format(pair_name))
        mock.get(CoinexchangeAdapter.RESOURCE_MARKETS,
                 text=coinex_markets_resp)
        mock.get(CoinexchangeAdapter.RESOURCE_TICKER_PARAM.format('251'),
                 text=coinex_market_summary_resp)
        mock.get(KrakenAdapter.RESOURCE, text=self.kraken_resp)
        mock.get(BaseTicker.BITFINEX_TICKER, text=self.bitifex_resp)
        mock.get(BaseTicker.FIAT_RATE_RESOURCE, text=self.fixer_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_SELL),
                 text=self.localbtc_sell_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_BUY),
                 text=self.localbtc_sell_resp)

    def get_tickers(self, mock):
        self.mock_resources(mock)
        get_all_tickers.apply()
