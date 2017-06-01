import json
from django.core.urlresolvers import reverse
from ticker.tests.base import TickerBaseTestCase
import requests_mock
from ticker.models import Price
from core.tests.utils import data_provider
from core.models import Pair


class TickerHistoryTestCase(TickerBaseTestCase):

    def setUp(self):
        super(TickerHistoryTestCase, self).setUp()
        self.pair = self.BTCEUR
        self.url = reverse('history-list',
                           kwargs={'pair': self.pair.name})
        # Disable unused pairs to reduce test time
        for pair in Pair.objects.exclude(pk=self.pair.pk):
            pair.disabled = True
            pair.save()

    def test_history_without_params_should_return_all_prices(self):
        history = json.loads(
            self.client.get(self.url).content.decode('utf-8')
        )
        prices = Price.objects.filter(pair=self.pair)
        self.assertEqual(len(history), len(prices))

    @data_provider(lambda: (
        (1, 2, '1 data points'),
        (2, 1, '2 data points'),
        (3, 1, '3 data points'),
        (5, 2, '5 data points'),
        (7, 3, '7 data points'),
        (11, 4, '11 data points'),
        (200, 0, '200 data points(more than there are prices)')),
    )
    def test_history_data_points(self, data_points, additional_tickers, name):
        with requests_mock.mock() as mock:
            for _ in range(additional_tickers):
                self.get_tickers(mock)
        prices = Price.objects.filter(pair=self.pair)
        if data_points > len(prices):
            data_points = len(prices)

        history = json.loads(
            self.client.get(
                self.url + '?data_points={}'.format(data_points)
            ).content.decode('utf-8')
        )
        self.assertEqual(
            len(history), data_points, '{}, history:{}'.format(name, history)
        )
