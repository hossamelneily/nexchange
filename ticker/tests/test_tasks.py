from ticker.models import Price
import requests_mock

from ticker.tests.base import TickerBaseTestCase


class TestTickerTask(TickerBaseTestCase):

    def setUp(self):
        super(TestTickerTask, self).setUp()
        self.main_ticker = self.BTCEUR
        self.main_ticker.disabled = False
        self.main_ticker.save()
        self.disabled_ticker = self.BTCUSD
        self.disabled_ticker.disabled = True
        self.disabled_ticker.save()

    @requests_mock.mock()
    def test_create_enabled_ticker(self, m):
        before = len(Price.objects.filter(pair=self.main_ticker))
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.main_ticker))
        self.assertEqual(before + 1, after)

    @requests_mock.mock()
    def test_do_not_create_disabled_ticker(self, m):
        before = len(Price.objects.filter(pair=self.disabled_ticker))
        self.get_tickers(m)
        after = len(Price.objects.filter(pair=self.disabled_ticker))
        self.assertEqual(before, after)
