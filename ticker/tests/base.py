import json

from core.tests.base import OrderBaseTestCase
from ticker.tasks.generic.base import BaseTicker
from ticker.task_summary import get_all_tickers
from ticker.adapters import KrakenAdapter, CryptopiaAdapter, \
    CoinexchangeAdapter, BittrexAdapter, BitgrailAdapter, IdexAdapter, \
    KucoinAdapter, BinanceAdapter, CobinhoodAdapter, BiboxAdapter, \
    HuobiAdapter, HitBTCAdapter
from ticker.tests.fixtures.coinexchange.markets import \
    response as coinex_markets_resp
from ticker.tests.fixtures.coinexchange.market_summary import \
    response as coinex_market_summary_resp
from ticker.tests.fixtures.kucoin.market_summary import \
    response as kucoin_market_summary_resp
from ticker.tests.fixtures.binance.market_summary import \
    response as binance_market_summary_resp
import requests_mock
from core.models import Pair
from ticker.tests.fixtures.cryptopia_ticker import res as \
    cryptopia_ticker_resp_empty
from ticker.tests.fixtures.bittrex.market_resp import \
    resp as bittrex_market_resp
from ticker.tests.fixtures.bitgrail.market_resp import \
    resp as bitgrail_market_resp
from ticker.tests.fixtures.cobinhood.market_resp import \
    resp as cobinhood_market_resp
from ticker.tests.fixtures.huobi.market_resp import \
    resp as huobi_market_resp
from ticker.tests.fixtures.bibox.market_resp import \
    resp as bibox_market_resp
from ticker.tests.fixtures.hitbtc.market_resp import \
    resp as hitbtc_market_resp


class TickerBaseTestCase(OrderBaseTestCase):

    DISABLE_NON_MAIN_PAIRS = True
    ENABLED_TICKER_PAIRS = ['ETHLTC', 'LTCBTC']
    ENABLE_FIAT = []

    @classmethod
    def setUpClass(cls):
        super(TickerBaseTestCase, cls).setUpClass()
        cls.ENABLE_FIAT = ['EUR']
        cls._read_fixtures_ticker()
        if cls.DISABLE_NON_MAIN_PAIRS:
            cls._disable_non_crypto_tickers()
        with requests_mock.mock() as mock:
            cls.get_tickers(mock)

    @classmethod
    def _disable_non_crypto_tickers(cls):
        pairs = Pair.objects.exclude(name__in=cls.ENABLED_TICKER_PAIRS)
        for pair in pairs:
            if all([pair.quote.code not in cls.ENABLE_FIAT]):
                pair.disable_ticker = True
                pair.save()

    @classmethod
    def _read_fixtures_ticker(cls):
        cryptopia_markets_path = 'ticker/tests/fixtures/cryptopia_markets.json'
        kraken_ticker_path = 'ticker/tests/fixtures/kraken_ticker.json'
        fixer_path = 'ticker/tests/fixtures/fixer.json'
        bitifex_path = 'ticker/tests/fixtures/bitifex.json'
        localbtc_buy_path = 'ticker/tests/fixtures/localbtc/buy.json'
        localbtc_sell_path = 'ticker/tests/fixtures/localbtc/sell.json'
        with open(cryptopia_markets_path) as f:
            cls.cryptopia_markets_resp = f.read().replace('\n', '')
        cls.cryptopia_ticker_resp = cryptopia_ticker_resp_empty
        with open(kraken_ticker_path) as f:
            cls.kraken_resp = f.read().replace('\n', '')
        cls.kraken_info = json.loads(cls.kraken_resp)['result']
        with open(fixer_path) as f:
            cls.fixer_resp = f.read().replace('\n', '')
        with open(bitifex_path) as f:
            cls.bitifex_resp = f.read().replace('\n', '')
        with open(localbtc_buy_path) as f:
            cls.localbtc_buy_resp = f.read().replace('\n', '')
        with open(localbtc_sell_path) as f:
            cls.localbtc_sell_resp = f.read().replace('\n', '')

    @classmethod
    def cryptopia_market_mapper(cls, pair):
        mapper = {
            'XVG/BTC': 1376,
            'DOGE/BTC': 102,
            'XVG/DOGE': 1378,
            'BCH/BTC': 5355
        }
        return mapper[pair]

    @classmethod
    def mock_resources(cls, mock):
        mock.get(
            CryptopiaAdapter.RESOURCE_MARKETS,
            text=cls.cryptopia_markets_resp)

        cryptopia_pairs = Pair.objects.filter(
            name__in=['BTCXVG', 'BTCDOGE', 'DOGEXVG', 'BTCBCH'])
        for pair in cryptopia_pairs:
            pair_name = '{}/{}'.format(pair.quote.code, pair.base.code)
            market_id = cls.cryptopia_market_mapper(pair_name)
            url = CryptopiaAdapter.RESOURCE_TICKER_PARAM.format(market_id)
            mock.get(
                url,
                text=cls.cryptopia_ticker_resp.format(pair_name))
        bittrex_pairs = Pair.objects.filter(
            name__in=['XVGBTC', 'DOGEBTC', 'ETHBTC', 'LTCBTC']
        )
        for pair in bittrex_pairs:
            if pair.base.code in ['ETH', 'LTC']:
                ask = 0.099
                bid = 0.098
            else:
                ask = 0.00000099
                bid = 0.00000098
            pair_name = '{}-{}'.format(pair.quote.code, pair.base.code)
            url = BittrexAdapter.BASE_URL + 'getticker/?market={}'.format(
                pair_name)
            resp_text = '{{"success":true,"message":"","result":{{"Bid":' \
                        '{bid},"Ask":{ask},"Last":{ask}}}}}'.format(ask=ask,
                                                                    bid=bid)
            mock.get(
                url,
                text=resp_text
            )
        bibox_pairs = Pair.objects.filter(name__in=['BIXBTC', 'BIXETH'])
        for pair in bibox_pairs:
            ask = 0.00014323
            bid = 0.00014272
            # ask = 7006.7264574
            # bid = 6981.7775606

            pair_name = '{}_{}'.format(pair.base.code, pair.quote.code)
            url = BiboxAdapter.BASE_URL + 'ticker&pair={}'.format(pair_name)
            resp_text = '{"result":{"pair":"BIX_BTC", "buy":"0.00014323", ' \
                        '"sell":"0.00014323"},"cmd":"ticker"}'
            mock.get(url, text=resp_text)

        huobi_pairs = Pair.objects.filter(name__in=['HTBTC', 'BTCHT'])
        for pair in huobi_pairs:
            ask = 0.000517040000000000
            bid = 0.000516570000000000
            pair_name = '{}{}'.format(pair.quote.code, pair.base.code).lower()
            url = HuobiAdapter.BASE_URL + 'market/detail/merged?symbol={}'\
                .format(pair_name)
            resp_text = \
                '{{"status":"ok","tick":{{"ask":[{},245.020000000000000000],' \
                '"bid":[{},8.510000000000000000]}}}}'.format(ask, bid)
            mock.get(url, text=resp_text)
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        mock.get(BitgrailAdapter.BASE_URL + 'markets',
                 text=bitgrail_market_resp)
        mock.get(CoinexchangeAdapter.RESOURCE_MARKETS,
                 text=coinex_markets_resp)
        mock.get(CoinexchangeAdapter.RESOURCE_TICKER_PARAM.format('251'),
                 text=coinex_market_summary_resp)
        mock.get(KrakenAdapter.RESOURCE, text=cls.kraken_resp)
        mock.get(BaseTicker.BITFINEX_TICKER, text=cls.bitifex_resp)
        mock.get(BaseTicker.FIAT_RATE_RESOURCE, text=cls.fixer_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_SELL),
                 text=cls.localbtc_sell_resp)
        mock.get(BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_BUY),
                 text=cls.localbtc_sell_resp)
        mock.post(IdexAdapter.BASE_URL + '/returnTicker',
                  text='{"last": "0.000322401"}')
        mock.get(KucoinAdapter.BASE_URL + 'open/tick',
                 text=kucoin_market_summary_resp)
        mock.get(BinanceAdapter.BASE_URL + 'ticker/allBookTickers',
                 text=binance_market_summary_resp)
        mock.get(CobinhoodAdapter.BASE_URL + 'tickers',
                 text=cobinhood_market_resp)
        mock.get(BiboxAdapter.BASE_URL + 'pairList',
                 text=bibox_market_resp)
        mock.get(HuobiAdapter.BASE_URL + 'v1/common/symbols',
                 text=huobi_market_resp)
        mock.get(HitBTCAdapter.BASE_URL + 'ticker',
                 text=hitbtc_market_resp)
        kraken_resp_text = \
            '{"result": {"XXBTZUSD": {"a": ["1077.50000"],"b": ["1069.20000"]}}}'
        mock.get(BaseTicker.KRAKEN_TICKER,
                 text=kraken_resp_text)

    @classmethod
    def get_tickers(cls, mock):
        cls.mock_resources(mock)
        get_all_tickers.apply()
