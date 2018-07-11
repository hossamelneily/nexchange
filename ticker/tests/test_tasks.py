from ticker.models import Price
import requests_mock

from ticker.tests.base import TickerBaseTestCase
from core.models import Pair, Market
from ticker.models import Ticker
from decimal import Decimal
from ticker.tasks.generic.base import BaseTicker, \
    KucoinAdapter, BinanceAdapter, BittrexAdapter
from unittest.mock import patch
from django.db.models import Q
from ticker.task_summary import get_ticker_crypto_crypto, \
    get_ticker_crypto_fiat, get_all_tickers_force, get_all_tickers


class TestTickerTask(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.DISABLE_NON_MAIN_PAIRS = False
        super(TestTickerTask, cls).setUpClass()
        cls.main_ticker = cls.BTCUSD
        cls.main_ticker.disable_ticker = False
        cls.main_ticker.save()
        cls.disabled_ticker = cls.BTCEUR
        cls.disabled_ticker.disable_ticker = True
        cls.disabled_ticker.save()

    @requests_mock.mock()
    def test_create_enabled_ticker(self, mock):
        # FIXME: remove after tokens tickers created
        enabled_pairs = Pair.objects.filter(disable_ticker=False)
        pending_tokens = []
        enabled_pairs = enabled_pairs.exclude(
            Q(quote__code__in=pending_tokens) | Q(base__code__in=pending_tokens))  # noqa)
        enabled_pairs_count = len(enabled_pairs)
        before = len(Price.objects.filter(pair=self.main_ticker,
                                          market__code='nex'))
        before_loc = len(Price.objects.filter(pair=self.main_ticker,
                                              market__code='locbit'))
        before_all = len(Price.objects.filter(market__code='nex'))
        self.get_tickers(mock)
        after = len(Price.objects.filter(pair=self.main_ticker,
                                         market__code='nex'))
        after_loc = len(Price.objects.filter(pair=self.main_ticker,
                                             market__code='locbit'))
        after_all = len(Price.objects.filter(market__code='nex'))
        self.assertEqual(before + 1, after)
        self.assertEqual(before_loc + 1, after_loc)
        self.assertEqual(before_all + enabled_pairs_count, after_all)

    def test_do_not_create_disabled_ticker(self):
        before = len(Price.objects.filter(pair=self.disabled_ticker))
        after = len(Price.objects.filter(pair=self.disabled_ticker))
        self.assertEqual(before, after)

    def test_ask_is_more_than_bid(self):
        self.disabled_ticker.disable_ticker = False
        self.disabled_ticker.save()
        tickers = Ticker.objects.all()
        for ticker in tickers:
            self.assertTrue(
                ticker.ask > ticker.bid,
                'ask({}) is not bigger than bid({}) on {}'.format(
                    ticker.ask, ticker.bid, ticker.pair
                )
            )

    def test_tickers_are_not_inverted(self):
        ''' This test case assumes that BTC is the most expensive currency '''
        self.disabled_ticker.disable_ticker = False
        self.disabled_ticker.save()
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
        bitfinex.return_value = {'ask': '1010.1', 'bid': '1009.1'}
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
            responds = api.get_api_adapter(pair)
            for res in responds:
                name = res.__class__.__name__.lower()
                self.assertIn(ticker_name, name)

    @patch('ticker.tasks.generic.base.BaseTicker.get_tickers')
    def test_choose_ticker_crypto(self,
                                  mock_get_tickers):
        pairs = []
        pairs.append(Pair.objects.get(name='BTCNANO'))
        pairs.append(Pair.objects.get(name='NANOLTC'))
        pairs.append(Pair.objects.get(name='BDGNANO'))
        max_ask = 1
        bid = 1
        mock_get_tickers.return_value = \
            [{'ask': Decimal(max_ask), 'bid': Decimal(bid)},
             {'ask': Decimal(max_ask * 0.75), 'bid': Decimal(bid)},
             {'ask': Decimal(max_ask * 0.8), 'bid': Decimal(bid)}]

        for pair in pairs:
            kwargs = {'pair_pk': pair.pk}
            get_ticker_crypto_crypto(**kwargs)
            price = Price.objects.filter(pair=pair).latest('id')
            expected_ask_with_fee = \
                Decimal(max_ask) * (Decimal('1.0') + pair.fee_ask)
            self.assertEquals(price.ticker.ask,
                              round(expected_ask_with_fee, 8))

    @patch("ticker.tasks.generic.base.BaseTicker.handle")
    @patch("ticker.tasks.generic.base.BaseTicker.get_tickers")
    @patch("ticker.tasks.generic.crypto_fiat_ticker."
           "CryptoFiatTicker.convert_fiat")
    def test_choose_ticker_fiat(self,
                                mock_convert_fiat,
                                mock_get_tickers,
                                mock_handle):
        max_ask = 1
        bid = 1
        usd_ask = 10633
        usd_bid = 9600
        eur_ask = usd_ask * 0.82
        eur_bid = usd_bid * 0.82
        mock_handle.return_value = \
            {'ask': {'price_usd': Decimal(usd_ask)},
             'bid': {'price_usd': Decimal(usd_bid)}}
        mock_get_tickers.return_value = \
            [{'ask': Decimal(max_ask * 0.85), 'bid': Decimal(bid * 0.85)},
             {'ask': Decimal(max_ask * 0.75), 'bid': Decimal(bid * 0.75)},
             {'ask': Decimal(max_ask), 'bid': Decimal(bid)}]
        pairs_crypto_eur = []
        pairs_crypto_usd = []
        pairs_crypto_eur.append(Pair.objects.get(name='NANOEUR'))
        pairs_crypto_usd.append(Pair.objects.get(name='NANOUSD'))
        mock_convert_fiat.return_value = \
            {'ask': Decimal(eur_ask),
             'bid': Decimal(eur_bid)}
        for pair_crypto_eur in pairs_crypto_eur:
            kwargs = {'pair_pk': pair_crypto_eur.pk}
            get_ticker_crypto_fiat(**kwargs)
            price = Price.objects.filter(pair=pair_crypto_eur).latest('id')
            expected_ask_with_fee = \
                Decimal('1.0') / Decimal(bid) * Decimal(eur_ask) * \
                (Decimal('1.0') + pair_crypto_eur.fee_ask)
            self.assertEquals(price.ticker.ask,
                              round(expected_ask_with_fee, 8))
        mock_convert_fiat.return_value = \
            {'ask': Decimal(usd_ask),
             'bid': Decimal(usd_bid)}
        for pair_crypto_usd in pairs_crypto_usd:
            kwargs = {'pair_pk': pair_crypto_usd.pk}
            get_ticker_crypto_fiat(**kwargs)
            price = Price.objects.filter(pair=pair_crypto_usd).latest('id')
            expected_ask_with_fee = \
                Decimal('1.0') / Decimal(bid) * Decimal(usd_ask) * \
                (Decimal('1.0') + pair_crypto_usd.fee_ask)
            self.assertEquals(price.ticker.ask,
                              round(expected_ask_with_fee, 8))

    @patch('ticker.adapters.BinanceAdapter.get_quote')
    @patch('ticker.adapters.KucoinAdapter.get_quote')
    @patch('ticker.adapters.BittrexAdapter.get_quote')
    def test_ignore_broken_adapter(self,
                                   mock_bittrex_get_quote,
                                   mock_kucoin_get_quote,
                                   mock_binance_get_quote):
        pairs = []
        pairs.append(Pair.objects.get(name='BTCNANO'))
        pairs.append(Pair.objects.get(name='BTCOMG'))
        kucoin_adapter = KucoinAdapter()
        bittrex_adapter = BittrexAdapter()
        binance_adapter = BinanceAdapter()
        api_adapters_list = \
            [[kucoin_adapter, bittrex_adapter],
             [kucoin_adapter, bittrex_adapter, binance_adapter]]
        ask = 1
        bid = 1
        mock_bittrex_get_quote.return_value = {
            'reverse': False,
            'ask': ask,
            'bid': bid,
        }
        mock_binance_get_quote.return_value = {
            'reverse': False,
            'ask': ask * 0.5,
            'bid': bid * 0.5,
        }
        mock_kucoin_get_quote.return_value = {
            'Broken adapter'
        }
        self.assertEquals(
            len(BaseTicker.get_tickers(BaseTicker,
                                       api_adapters_list[0],
                                       pairs[0])),
            1)
        self.assertEquals(
            len(BaseTicker.get_tickers(BaseTicker,
                                       api_adapters_list[1],
                                       pairs[1])),
            2)


class TestTickerTaskPartial(TickerBaseTestCase):
    @patch('ticker.models.Ticker._validate_change')
    @requests_mock.mock()
    def test_get_all_tickers_force(self, _validate_change, mock):
        self._disable_non_crypto_tickers()
        _validate_change.side_effect = ValueError('ba dumt tss')
        self.mock_resources(mock)
        get_all_tickers.apply()
        self.assertEqual(
            Pair.objects.filter(disable_ticker=False,
                                last_price_saved=False).count(),
            Pair.objects.filter(disable_ticker=False).count(),
        )
        get_all_tickers_force.apply()
        self.assertEqual(
            Pair.objects.filter(disable_ticker=False,
                                last_price_saved=False).count(),
            0
        )
