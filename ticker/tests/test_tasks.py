from ticker.models import Price
import requests_mock

from ticker.tests.base import TickerBaseTestCase
from core.models import Pair
from ticker.models import Ticker


class TestTickerTask(TickerBaseTestCase):

    def setUp(self):
        super(TestTickerTask, self).setUp()
        self.main_ticker = self.BTCEUR
        self.main_ticker.disable_ticker = False
        self.main_ticker.save()
        self.disabled_ticker = self.BTCUSD
        self.disabled_ticker.disable_ticker = True
        self.disabled_ticker.save()

    @requests_mock.mock()
    def test_create_enabled_ticker(self, m):
        enabled_pairs_count = len(Pair.objects.filter(disable_ticker=False))
        before = len(Price.objects.filter(pair=self.main_ticker))
        before_all = len(Price.objects.all())
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.main_ticker))
        after_all = len(Price.objects.all())
        self.assertEqual(before + 1, after)
        self.assertEqual(before_all + enabled_pairs_count, after_all)

    @requests_mock.mock()
    def test_do_not_create_disabled_ticker(self, m):
        before = len(Price.objects.filter(pair=self.disabled_ticker))
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.disabled_ticker))
        self.assertEqual(before, after)

    @requests_mock.mock()
    def test_ask_is_more_then_bid(self, m):
        self.disabled_ticker.disable_ticker = True
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
