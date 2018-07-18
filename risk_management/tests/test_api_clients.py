from risk_management.tests.base import RiskManagementBaseTestCase
from core.models import Pair
from nexchange.api_clients.bittrex import BittrexApiClient
import requests_mock
from ticker.tests.fixtures.bittrex.market_resp import \
    resp as bittrex_market_resp
from ticker.adapters import BittrexAdapter


class TradingPairPickingTestCase(RiskManagementBaseTestCase):

    def setUp(self):
        super(TradingPairPickingTestCase, self).setUp()
        self.bittrex_client = BittrexApiClient()

    @requests_mock.mock()
    def test_direct_pair(self, mock):
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        xvgbtc = Pair.objects.get(name='XVGBTC')
        xvgbtc_resp = self.bittrex_client.get_api_pairs_for_pair(xvgbtc)
        self.assertEqual(
            xvgbtc_resp,
            {xvgbtc: {
                'main_currency': xvgbtc.base,
                'api_pair_name': 'BTC-XVG',
            }}
        )

    @requests_mock.mock()
    def test_reverse_pair(self, mock):
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        bchbtc = Pair.objects.get(name='BCHBTC')
        btcbch = bchbtc.reverse_pair
        btcbch_resp = self.bittrex_client.get_api_pairs_for_pair(btcbch)
        self.assertEqual(
            btcbch_resp,
            {bchbtc: {
                'main_currency': bchbtc.base,
                'api_pair_name': 'BTC-BCH'
            }}
        )

    @requests_mock.mock()
    def test_transition_pair(self, mock):
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        zecxvg = Pair.objects.get(name='ZECXVG')
        zecbtc = Pair.objects.get(name='ZECBTC')
        xvgbtc = Pair.objects.get(name='XVGBTC')
        zecxvg_resp = self.bittrex_client.get_api_pairs_for_pair(zecxvg)
        self.assertEqual(
            zecxvg_resp,
            {
                zecbtc: {
                    'main_currency': zecbtc.base,
                    'api_pair_name': 'BTC-ZEC'
                },
                xvgbtc: {
                    'main_currency': xvgbtc.base,
                    'api_pair_name': 'BTC-XVG'
                },
            }
        )
