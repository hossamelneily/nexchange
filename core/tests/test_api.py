import json
from django.core.urlresolvers import reverse
from unittest import skip
from core.tests.base import OrderBaseTestCase
from rest_framework.test import APIClient
from risk_management.models import Account
from core.models import Pair
from decimal import Decimal


class CoreApiTestCase(OrderBaseTestCase):

    def setUp(self):
        self.api_client = APIClient()
        self.pair_url = '/en/api/v1/pair/'

    def tearDown(self):
        pass

    def _check_dynamic_test_mode(self, pair_name,
                                 expected_dynamic_test_mode, data,
                                 expected_db_test_mode=False):
        pair = Pair.objects.get(name=pair_name)
        self.assertEqual(pair.test_mode, expected_db_test_mode)
        dynamic_test_mode = \
            [p['test_mode'] for p in data if p['name'] == pair_name][0]
        self.assertEqual(dynamic_test_mode, expected_dynamic_test_mode)

    def test_pair_api(self):
        # DB SETUP
        # BTC target level
        btc_account = Account.objects.get(is_main_account=True,
                                          reserve__currency__code='BTC')
        btc_account.available = btc_account.reserve.target_level
        btc_account.save()
        # ETH too much
        eth_account = Account.objects.get(is_main_account=True,
                                          reserve__currency__code='ETH')
        eth_account.available = \
            eth_account.reserve.maximum_level * Decimal('1.01')
        eth_account.save()
        # LTC to little
        ltc_account = Account.objects.get(is_main_account=True,
                                          reserve__currency__code='LTC')
        ltc_account.available = \
            ltc_account.reserve.minimum_level * Decimal('0.99')
        ltc_account.save()
        # XVG target level
        xvg_account = Account.objects.get(is_main_account=True,
                                          reserve__currency__code='XVG')
        xvg_account.available = xvg_account.reserve.target_level
        xvg_account.save()
        # Move XVGBTC to test_mode
        xvgbtc = Pair.objects.get(name='XVGBTC')
        xvgbtc.test_mode = True
        xvgbtc.save()

        # API CALL
        data = self.api_client.get(self.pair_url).json()

        # ASSERTIONS
        # Check BTCLTC, should be ok (test_mode == False)
        self._check_dynamic_test_mode('BTCLTC', False, data)
        # Check LTCBTC, LTC to little (test_mode == True)
        self._check_dynamic_test_mode('LTCBTC', True, data)
        # Check BTCETH, ETH to much (test_mode == True)
        self._check_dynamic_test_mode('BTCETH', True, data)
        # Check ETHBTC, should be ok (test_mode == False)
        self._check_dynamic_test_mode('ETHBTC', False, data)
        # Check XVGBTC, db test mode True - all True
        self._check_dynamic_test_mode('XVGBTC', True, data,
                                      expected_db_test_mode=True)
        # Check LTCEUR, LTC to little (test_mode == True)
        self._check_dynamic_test_mode('LTCEUR', True, data)
        # Check BTCUSD, should be ok (test_mode == False)
        self._check_dynamic_test_mode('BTCUSD', False, data)


class PairsTestCase(OrderBaseTestCase):

    def setUp(self):
        super(PairsTestCase, self).setUp()
        self.url = reverse('pair-list')
        self.pairs = json.loads(
            self.client.get(self.url).content.decode('utf-8')
        )

    def test_pairs_without_params_should_return_all_pairs(self):
        self.assertGreater(len(self.pairs), 0)

    def check_pair_data(self, pair):
        expected_name = pair['base'] + pair['quote']
        self.assertEqual(expected_name, pair['name'])
        self.assertGreaterEqual(float(pair['fee_ask']), 0)
        self.assertGreaterEqual(float(pair['fee_bid']), 0)

        for key in pair:
            self.assertIsNotNone(pair[key])

    def test_pairs_without_params_list_correct_fields(self):
        for pair in self.pairs:
            self.check_pair_data(pair)

        self.assertGreater(len(self.pairs), 0)

    @skip('Breaks when caching is on')
    def test_pairs_detail_should_return_single_pair(self):
        for pair in self.pairs:
            pair_detail_url = reverse(
                'pair-detail', kwargs={'name': pair['name']})
            pair_detail = json.loads(
                self.client.get(pair_detail_url).content.decode('utf-8')
            )

            self.check_pair_data(pair_detail)
