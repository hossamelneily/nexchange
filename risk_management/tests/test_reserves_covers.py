from risk_management.tests.base import RiskManagementBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from risk_management.models import ReservesCover, Reserve, Cover
from decimal import Decimal
from risk_management.task_summary import execute_reserves_cover
import requests_mock
from ticker.tests.fixtures.bittrex.market_resp import \
    resp as bittrex_market_resp
from ticker.adapters import BittrexAdapter
from core.models import Pair
from core.tests.base import SCRYPT_ROOT, BITTREX_ROOT
from unittest.mock import patch


def bittrex_rate_callback(request, context):
    query = request.query
    error_msg = 'Not Mocked, {} '.format(query)
    res = {
        'success': False,
        'message': error_msg,
        'result': error_msg
    }
    if query == 'market=btc-doge':
        res = {
            'success': True,
            'result': {
                'Bid': 0.00000053, 'Ask': 0.00000054
            }
        }
    elif query == 'market=btc-xvg':
        res = {
            'success': True,
            'result': {
                'Bid': 0.00000820, 'Ask': 0.00000821
            }
        }
    return res


class ReservesCoversTestCase(RiskManagementBaseTestCase, TickerBaseTestCase):

    fixtures = TickerBaseTestCase.fixtures

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['DOGEXVG', 'DOGEBTC', 'XVGBTC', 'BTCXVG',
             'BTCDOGE', 'XVGDOGE']
        super(ReservesCoversTestCase, cls).setUpClass()

    def setUp(self):
        super(ReservesCoversTestCase, self).setUp()
        self.doge_reserve = Reserve.objects.get(currency__code='DOGE')
        self.xvg_reserve = Reserve.objects.get(currency__code='XVG')
        self.btc_reserve = Reserve.objects.get(currency__code='BTC')
        self.doge_trade_account = self.doge_reserve.account_set.get(
            description='Bittrex'
        )
        self.xvg_trade_account = self.xvg_reserve.account_set.get(
            description='Bittrex'
        )
        for reserve in Reserve.objects.all():
            self._set_level(reserve)
        self.bad_main_currency_resp = {
            Pair.objects.get(name='DOGEBTC'): {
                'api_pair_name': 'BTC-DOGE',
                'main_currency': self.btc_reserve.currency
            },
            Pair.objects.get(name='XVGBTC'): {
                'api_pair_name': 'BTC-XVG',
                'main_currency': self.btc_reserve.currency
            }
        }

    def _set_level(self, reserve, diff=0):
        main_account = reserve.main_account
        main_account.available = \
            reserve.target_level + reserve.allowed_diff * Decimal(diff)
        main_account.save()

    @requests_mock.mock()
    @patch('risk_management.task_summary.execute_reserves_cover.retry')
    @patch(BITTREX_ROOT + 'get_main_address')
    @patch(BITTREX_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_create_covers_doge_xvg(self, mock, release_coins, s_health,
                                    b_health, b_main_address, retry_patch):
        internal_tx_id = self.generate_txn_id()
        s_health.return_value = b_health.return_value = True
        b_main_address.return_value = 'bittrex_addrerss'
        release_coins.return_value = internal_tx_id, True
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        self._set_level(self.doge_reserve, diff=-2)
        self._set_level(self.xvg_reserve, diff=2)

        mock.get(BittrexAdapter.BASE_URL + 'getticker',
                 json=bittrex_rate_callback)
        sell_id = self.generate_txn_id()
        mock.get('https://bittrex.com/api/v1.1/market/selllimit',
                 json={'success': True, 'result': {'uuid': sell_id}})
        buy_id = self.generate_txn_id()
        mock.get('https://bittrex.com/api/v1.1/market/buylimit',
                 json={'success': True, 'result': {'uuid': buy_id}})
        with patch('risk_management.models.'
                   'bittrex_api.get_api_pairs_for_pair') as pair_resp:
            pair_resp.return_value = self.bad_main_currency_resp
            bad_reserve_cover = ReservesCover()
            bad_reserve_cover.save()
            self.assertEqual(bad_reserve_cover.pair.name, 'DOGEXVG')
            self.assertEqual(bad_reserve_cover.cover_set.all().count(), 0)

        reserve_cover = ReservesCover()
        reserve_cover.save()
        reserve_cover.create_cover_objects()
        self.assertEqual(reserve_cover.pair.name, 'DOGEXVG')
        sell_cover = reserve_cover.cover_set.get(pair__name='XVGBTC')
        self.assertEqual(sell_cover.cover_type, Cover.SELL)
        self.assertEqual(sell_cover.account, self.xvg_trade_account)
        buy_cover = reserve_cover.cover_set.get(pair__name='DOGEBTC')
        self.assertEqual(buy_cover.cover_type, Cover.BUY)
        self.assertEqual(buy_cover.account, self.doge_trade_account)
        self.assertEqual(buy_cover.amount_quote, sell_cover.amount_quote)
        reserve_cover.refresh_from_db()
        self.assertEqual(reserve_cover.amount_base, buy_cover.amount_base)
        self.assertEqual(reserve_cover.amount_quote, sell_cover.amount_base)

        # fund exchange wallet
        execute_reserves_cover(reserve_cover.pk)
        # second time to check if multiple transactions isnt created
        self.assertEqual(retry_patch.call_count, 1)
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 2)
        tx = reserve_cover.transaction_set.get()
        self.assertEqual(tx.amount, sell_cover.amount_base * Decimal('1.01'))
        self.assertEqual(tx.currency, sell_cover.pair.base)
        self.assertEqual(tx.address_to.address, b_main_address.return_value)
        release_coins.assert_called_once()

        # execute SELL
        _account = buy_cover.account.get_same_api_wallet(sell_cover.pair.base)
        _account.available = sell_cover.amount_base
        _account.save()
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 3)
        sell_cover.refresh_from_db()
        buy_cover.refresh_from_db()
        self.assertEqual(sell_cover.cover_id, sell_id)
        self.assertEqual(sell_cover.status, Cover.EXECUTED)
        self.assertEqual(buy_cover.status, Cover.INITIAL)

        # execute BUY
        _account = buy_cover.account.get_same_api_wallet(buy_cover.pair.quote)
        _account.available = buy_cover.amount_quote
        _account.save()
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 3)
        buy_cover.refresh_from_db()
        self.assertEqual(buy_cover.cover_id, buy_id)
        self.assertEqual(buy_cover.status, Cover.EXECUTED)

    @requests_mock.mock()
    @patch('risk_management.task_summary.execute_reserves_cover.retry')
    @patch(BITTREX_ROOT + 'get_main_address')
    @patch(BITTREX_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_create_covers_doge_btc(self, mock, release_coins, s_health,
                                    b_health, b_main_address, retry_patch):
        internal_tx_id = self.generate_txn_id()
        s_health.return_value = b_health.return_value = True
        b_main_address.return_value = 'bittrex_addrerss'
        release_coins.return_value = internal_tx_id, True
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        self._set_level(self.doge_reserve, diff=-2)
        self._set_level(self.btc_reserve, diff=2)

        mock.get(BittrexAdapter.BASE_URL + 'getticker',
                 json=bittrex_rate_callback)
        buy_id = self.generate_txn_id()
        mock.get('https://bittrex.com/api/v1.1/market/buylimit',
                 json={'success': True, 'result': {'uuid': buy_id}})
        with patch('risk_management.models.'
                   'bittrex_api.get_api_pairs_for_pair') as pair_resp:
            pair_resp.return_value = self.bad_main_currency_resp
            bad_reserve_cover = ReservesCover()
            bad_reserve_cover.save()
            self.assertEqual(bad_reserve_cover.pair.name, 'DOGEBTC')
            self.assertEqual(bad_reserve_cover.cover_set.all().count(), 0)
        reserve_cover = ReservesCover()
        reserve_cover.save()
        self.assertEqual(bad_reserve_cover.pair.name, 'DOGEBTC')
        reserve_cover.create_cover_objects()
        buy_cover = reserve_cover.cover_set.get()
        self.assertEqual(buy_cover.account, self.doge_trade_account)
        self.assertEqual(buy_cover.pair.name, 'DOGEBTC')
        self.assertEqual(buy_cover.cover_type, Cover.BUY)
        reserve_cover.refresh_from_db()
        self.assertEqual(reserve_cover.amount_base, buy_cover.amount_base)
        self.assertEqual(reserve_cover.amount_quote, buy_cover.amount_quote)

        # fund exchange wallet
        execute_reserves_cover(reserve_cover.pk)
        # second time to check if multiple transactions isnt created
        self.assertEqual(retry_patch.call_count, 1)
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 2)
        tx = reserve_cover.transaction_set.get()
        self.assertEqual(tx.amount, buy_cover.amount_quote * Decimal('1.01'))
        self.assertEqual(tx.currency, buy_cover.pair.quote)
        self.assertEqual(tx.address_to.address, b_main_address.return_value)
        release_coins.assert_called_once()

        # execute
        _account = buy_cover.account.get_same_api_wallet(buy_cover.pair.quote)
        _account.available = buy_cover.amount_quote
        _account.save()
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 2)
        buy_cover.refresh_from_db()
        self.assertEqual(buy_cover.cover_id, buy_id)
        self.assertEqual(buy_cover.status, Cover.EXECUTED)

    @requests_mock.mock()
    @patch('risk_management.task_summary.execute_reserves_cover.retry')
    @patch(BITTREX_ROOT + 'get_main_address')
    @patch(BITTREX_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'health_check')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_create_covers_btc_xvg(self, mock, release_coins, s_health,
                                   b_health, b_main_address, retry_patch):
        internal_tx_id = self.generate_txn_id()
        s_health.return_value = b_health.return_value = True
        b_main_address.return_value = 'bittrex_addrerss'
        release_coins.return_value = internal_tx_id, True
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        self._set_level(self.btc_reserve, diff=-2)
        self._set_level(self.xvg_reserve, diff=2)

        mock.get(BittrexAdapter.BASE_URL + 'getticker',
                 json=bittrex_rate_callback)
        sell_id = self.generate_txn_id()
        mock.get('https://bittrex.com/api/v1.1/market/selllimit',
                 json={'success': True, 'result': {'uuid': sell_id}})
        with patch('risk_management.models.'
                   'bittrex_api.get_api_pairs_for_pair') as pair_resp:
            pair_resp.return_value = self.bad_main_currency_resp
            bad_reserve_cover = ReservesCover()
            bad_reserve_cover.save()
            self.assertEqual(bad_reserve_cover.pair.name, 'BTCXVG')
            self.assertEqual(bad_reserve_cover.cover_set.all().count(), 0)
        reserve_cover = ReservesCover()
        reserve_cover.save()
        reserve_cover.create_cover_objects()
        sell_cover = reserve_cover.cover_set.get()
        self.assertEqual(sell_cover.account, self.xvg_trade_account)
        self.assertEqual(sell_cover.pair.name, 'XVGBTC')
        self.assertEqual(sell_cover.cover_type, Cover.SELL)
        reserve_cover.refresh_from_db()
        self.assertEqual(reserve_cover.amount_quote, sell_cover.amount_base)
        self.assertEqual(reserve_cover.amount_base, sell_cover.amount_quote)

        # fund exchange wallet
        execute_reserves_cover(reserve_cover.pk)
        # second time to check if multiple transactions isnt created
        self.assertEqual(retry_patch.call_count, 1)
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 2)
        tx = reserve_cover.transaction_set.get()
        self.assertEqual(tx.amount, sell_cover.amount_base * Decimal('1.01'))
        self.assertEqual(tx.currency, sell_cover.pair.base)
        self.assertEqual(tx.address_to.address, b_main_address.return_value)
        release_coins.assert_called_once()
        # execute
        _account = sell_cover.account.get_same_api_wallet(sell_cover.pair.base)
        _account.available = sell_cover.amount_base
        _account.save()
        execute_reserves_cover(reserve_cover.pk)
        self.assertEqual(retry_patch.call_count, 2)
        sell_cover.refresh_from_db()
        self.assertEqual(sell_cover.cover_id, sell_id)
        self.assertEqual(sell_cover.status, Cover.EXECUTED)

    def test_reserves_cover_settings_remove_currencies(self):
        self._set_level(self.btc_reserve, diff=-2)
        self._set_level(self.xvg_reserve, diff=2)
        reserve_cover = ReservesCover()
        reserve_cover.save()
        settings = reserve_cover.settings
        settings_currencies = settings.currencies.all()
        self.assertIn(self.btc_reserve.currency, settings_currencies)
        self.assertIn(self.xvg_reserve.currency, settings_currencies)
        self.assertEqual(reserve_cover.buy_reserves,
                         reserve_cover.buy_reserves_filtered)
        self.assertEqual(reserve_cover.sell_reserves,
                         reserve_cover.sell_reserves_filtered)
        settings.currencies.remove(self.xvg_reserve.currency,
                                   self.btc_reserve.currency)
        self.assertEqual(reserve_cover.buy_reserves_filtered, [])
        self.assertEqual(reserve_cover.sell_reserves_filtered, [])

    def test_create_clear_cover(self):
        reserve_cover = ReservesCover()
        reserve_cover.save()
