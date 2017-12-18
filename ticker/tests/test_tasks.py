from ticker.models import Price
import requests_mock

from ticker.tests.base import TickerBaseTestCase
from core.models import Pair, Market
from ticker.models import Ticker
from decimal import Decimal
from ticker.tasks.generic.base import BaseTicker
from unittest.mock import patch
from django.db.models import Q


class TestTickerTask(TickerBaseTestCase):

    def setUp(self):
        self.DISABLE_NON_MAIN_PAIRS = False
        super(TestTickerTask, self).setUp()
        self.main_ticker = self.BTCUSD
        self.main_ticker.disable_ticker = False
        self.main_ticker.save()
        self.disabled_ticker = self.BTCEUR
        self.disabled_ticker.disable_ticker = True
        self.disabled_ticker.save()

    @requests_mock.mock()
    def test_create_enabled_ticker(self, m):
        # FIXME: remove after tokens tickers created
        enabled_pairs = Pair.objects.filter(disable_ticker=False)
        pending_tokens = ['BDG']
        enabled_pairs = enabled_pairs.exclude(
            Q(quote__code__in=pending_tokens) | Q(base__code__in=pending_tokens))  # noqa)
        enabled_pairs_count = len(enabled_pairs)
        before = len(Price.objects.filter(pair=self.main_ticker,
                                          market__code='nex'))
        before_loc = len(Price.objects.filter(pair=self.main_ticker,
                                              market__code='locbit'))
        before_all = len(Price.objects.filter(market__code='nex'))
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.main_ticker,
                                         market__code='nex'))
        after_loc = len(Price.objects.filter(pair=self.main_ticker,
                                             market__code='locbit'))
        after_all = len(Price.objects.filter(market__code='nex'))
        self.assertEqual(before + 1, after)
        self.assertEqual(before_loc + 1, after_loc)
        self.assertEqual(before_all + enabled_pairs_count, after_all)

    @requests_mock.mock()
    def test_do_not_create_disabled_ticker(self, m):
        before = len(Price.objects.filter(pair=self.disabled_ticker))
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.disabled_ticker))
        self.assertEqual(before, after)

    @requests_mock.mock()
    def test_ask_is_more_then_bid(self, m):
        self.disabled_ticker.disable_ticker = False
        self.disabled_ticker.save()
        self.get_tickers(m)
        tickers = Ticker.objects.all()
        for ticker in tickers:
            self.assertTrue(
                ticker.ask > ticker.bid,
                'ask({}) is not bigger then bid({}) on {}'.format(
                    ticker.ask, ticker.bid, ticker.pair
                )
            )

    @requests_mock.mock()
    def test_tickers_are_not_inverted(self, m):
        ''' This test case assumes that BTC is the most expensive currency '''
        self.disabled_ticker.disable_ticker = False
        self.disabled_ticker.save()
        self.get_tickers(m)
        tickers_base_btc = Ticker.objects.filter(pair__base=self.BTC)
        for ticker in tickers_base_btc:
            self.assertTrue(
                ticker.ask > Decimal('1.0'),
                'ask {} for {} less then 1.0. Check, if ticker is '
                'not inverted!!!!'.format(
                    ticker.ask, ticker.pair.name
                )
            )
            self.assertTrue(
                ticker.bid > Decimal('1.0'),
                'bid {} for {} less then 1.0. Check, if ticker is '
                'not inverted!!!!'.format(
                    ticker.bid, ticker.pair.name
                )
            )
        tickers_quote_btc = Ticker.objects.filter(pair__quote=self.BTC)
        for ticker in tickers_quote_btc:
            self.assertTrue(
                ticker.ask < Decimal('1.0'),
                'ask {} for {} more then 1.0. Check, if ticker is '
                'not inverted!!!!'.format(
                    ticker.ask, ticker.pair.name
                )
            )
            self.assertTrue(
                ticker.bid < Decimal('1.0'),
                'bid {} for {} more then 1.0. Check, if ticker is '
                'not inverted!!!!'.format(
                    ticker.bid, ticker.pair.name
                )
            )

    @patch('ticker.tasks.generic.base.BaseTicker.get_price')
    @patch('ticker.tasks.generic.base.BaseTicker._get_bitfinex_usd_ticker')
    def test_handle_localbtc(self, bitfinex, locbit):
        bitfinex.return_value = {}
        locbit.return_value = {}
        pair = Pair.objects.get(name='BTCUSD')
        api = BaseTicker()
        api.pair = pair
        nex_market = Market.objects.get(code='nex')
        loc_market = Market.objects.get(code='locbit')
        api = BaseTicker()
        api.pair = pair
        api.market = nex_market
        api.handle()
        self.assertEqual(1, bitfinex.call_count)
        self.assertEqual(0, locbit.call_count)
        api.market = loc_market
        api.handle()
        self.assertEqual(2, bitfinex.call_count)
        self.assertEqual(2, locbit.call_count)

    def test_get_api_adapter(self):
        api = BaseTicker()
        pair = Pair.objects.get(name='BTCLTC')
        ticker_names = ['kraken', 'cryptopia', 'coinexchange', '']
        for ticker_name in ticker_names:
            pair.quote.ticker = ticker_name
            res = api.get_api_adapter(pair)
            if ticker_name:
                name = res.__class__.__name__.lower()
                self.assertIn(ticker_name, name)
            else:
                self.assertEqual(api.bitcoin_api_adapter, res)
