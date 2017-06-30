from ticker.adapters import CoinexchangeAdapter
from unittest.mock import patch
from core.tests.base import OrderBaseTestCase
from core.models import Pair
from ticker.tests.fixtures.coinexchange.markets import \
    response as coinex_markets_resp
from ticker.tests.fixtures.coinexchange.market_summary import \
    response as coinex_market_summary_resp
from ticker.tests.fixtures.coinexchange.market_summary_bad_id import \
    response as coinex_market_summary_bad_id_resp
import requests_mock
from core.tests.utils import data_provider


class CoinexchangeAdapterTestCase(OrderBaseTestCase):

    def setUp(self):
        super(CoinexchangeAdapterTestCase, self).setUp()
        self.adapter = CoinexchangeAdapter()

    @data_provider(
        lambda: (
            ('BTCRNS', ['251']),
            ('BTCLTC', ['18']),
            ('BTCETH', ['87']),
            # !!!Be aware of RubbleCoin!!!
            ('BTCRUB', []),
            ('BTCEUR', []),
        )
    )
    @requests_mock.mock()
    def test_get_markets_ids(self, pair_name, expected_res, mock):
        mock.get(self.adapter.RESOURCE_MARKETS, text=coinex_markets_resp)
        pair = Pair.objects.get(name=pair_name)
        market_ids = self.adapter.get_markets_ids(pair)
        self.assertEqual(market_ids, expected_res, pair_name)

    @data_provider(
        lambda: (
                ('Good id', 'good_id', coinex_market_summary_resp, True),
                ('Bad id', 'bad_id', coinex_market_summary_bad_id_resp, False),
        )
    )
    @requests_mock.mock()
    def test_get_ticker(self, name, market_id, response, success, mock):
        mock.get(self.adapter.RESOURCE_TICKER_PARAM.format(market_id),
                 text=response)
        res = self.adapter.get_ticker(market_id)
        if success:
            self.assertIn('ask', res, name)
            self.assertIn('bid', res, name)
        else:
            self.assertIn('error', res, name)

    @data_provider(
        lambda: (
            ('No market error', []),
            ('Several markets error', ['1', '2']),
        )
    )
    @patch('ticker.adapters.CoinexchangeAdapter.get_markets_ids')
    def test_get_quote_errors(self, name, ids_return_val, market_ids):
        market_ids.return_value = ids_return_val
        pair = Pair.objects.last()
        quote = self.adapter.get_quote(pair)
        self.assertIn('error', quote, name)

    @data_provider(
        lambda: (
                ('BTCRNS', '251'),
        )
    )
    @requests_mock.mock()
    def test_get_quote(self, pair_name, market_id, mock):
        mock.get(self.adapter.RESOURCE_MARKETS, text=coinex_markets_resp)
        mock.get(self.adapter.RESOURCE_TICKER_PARAM.format(market_id),
                 text=coinex_market_summary_resp)
        pair = Pair.objects.get(name=pair_name)
        quote = self.adapter.get_quote(pair)
        self.assertIn('ask', quote)
        self.assertIn('bid', quote)
