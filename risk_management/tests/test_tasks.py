from risk_management.tests.base import RiskManagementBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from unittest.mock import patch
from risk_management.task_summary import reserves_balance_checker_periodic,\
    account_balance_checker_invoke, reserve_balance_maintainer_invoke,\
    main_account_filler_invoke, currency_reserve_balance_checker_invoke, \
    currency_cover_invoke, log_current_assets, calculate_pnls, \
    disable_currency_base, disable_currency_quote,\
    enable_currency_base, enable_currency_quote
from risk_management.models import Reserve, Account, Cover, PortfolioLog,\
    PNLSheet, DisabledCurrency
from decimal import Decimal
from core.tests.utils import data_provider
from core.models import Pair, Currency, Address, AddressReserve
from nexchange.api_clients.kraken import KrakenApiClient
from nexchange.api_clients.bittrex import BittrexApiClient
from core.tests.base import ETH_ROOT, SCRYPT_ROOT, BLAKE2_ROOT, \
    OMNI_ROOT, CRYPTONIGHT_ROOT
from orders.models import Order
from rest_framework.test import APIClient
import os


RPC2_PUBLIC_KEY_C1 = 'DOGEaddress'
RPC3_PUBLIC_KEY_C1 = 'VERGEaddress'


class BalanceTaskTestCase(RiskManagementBaseTestCase):

    def setUp(self):
        super(BalanceTaskTestCase, self).setUp()
        accounts = Account.objects.all()
        for account in accounts:
            account.disabled = False
            account.save()
        self.reserve = Reserve.objects.get(currency__code='XVG')

    @patch(BLAKE2_ROOT + 'get_balance')
    @patch('nexchange.api_clients.uphold.Uphold.get_card')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch(SCRYPT_ROOT + 'get_balance')
    @patch(ETH_ROOT + 'get_balance')
    @patch(OMNI_ROOT + 'get_balance')
    @patch(CRYPTONIGHT_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_check_all_reserves_balances(self, get_balance_bit,
                                         get_balance_cryptonight,
                                         get_balance_omni, get_balance_eth,
                                         get_balance_rpc,
                                         get_balance_kraken,
                                         get_card, get_balance_blake2):
        balance = 800.0
        available = 500.0
        pending = balance - available
        get_balance_bit.return_value = self._get_bittrex_get_balance_response(
            balance, available, pending)
        get_balance_rpc.return_value = get_balance_eth.return_value = \
            get_balance_blake2.return_value = get_balance_omni.return_value = \
            get_balance_cryptonight.return_value = Decimal(str(balance))
        get_balance_kraken.return_value = {'result': {'XXDG': str(balance)}}
        get_card.return_value = {'balance': Decimal(balance),
                                 'available': Decimal(available)}
        reserves_balance_checker_periodic.apply_async()
        reserves = Reserve.objects.all()
        # Log the the assets:
        log_current_assets.apply_async()
        portfolio_log = PortfolioLog.objects.last()
        for reserve in reserves:
            accounts = reserve.account_set.all()
            all_balance = all_pending = all_available = Decimal('0')
            for account in accounts:
                self.assertEqual(account.balance, Decimal(str(balance)))
                if account.wallet in ['api3', 'api1']:
                    self.assertEqual(account.available,
                                     Decimal(str(available)))
                    self.assertEqual(account.pending, Decimal(str(pending)))
                else:
                    self.assertEqual(account.available, Decimal(str(balance)))
                    self.assertEqual(account.pending, Decimal('0'))
                all_balance += account.balance
                all_available += account.available
                all_pending += account.pending

            msg = 'reserve: {}'.format(reserve)
            self.assertEqual(reserve.balance, all_balance, msg)
            self.assertEqual(reserve.available, all_available, msg)
            self.assertEqual(reserve.pending, all_pending, msg)
            reserve_log = portfolio_log.reservelog_set.get(reserve=reserve)
            self.assertEqual(reserve_log.available, reserve.available, msg)
        # Check portfolio properties
        self.assertIsInstance(portfolio_log.assets_by_proportion, dict)
        self.assertIsInstance(portfolio_log.assets_str, str)
        self.assertIsInstance(portfolio_log.total_btc, Decimal)
        self.assertIsInstance(portfolio_log.total_usd, Decimal)
        self.assertIsInstance(portfolio_log.total_eth, Decimal)
        self.assertIsInstance(portfolio_log.total_eur, Decimal)
        self.assertIsInstance(portfolio_log.__str__(), str)

    @data_provider(
        lambda: (
            ('XVG bittrex',
             {'reserve__currency__code': 'XVG', 'wallet': 'api3'}),
            ('DOGE kraken',
             {'reserve__currency__code': 'DOGE', 'wallet': 'api2'}),
            ('BTC uphold',
             {'reserve__currency__code': 'BTC', 'wallet': 'api1'}),
        )
    )
    @patch('nexchange.api_clients.uphold.Uphold.get_card')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_check_account_balance(self, name, filters, _get_balance_bit,
                                   _get_balance_kraken, _get_card):
        balance = 800.0
        available = 500.0
        pending = balance - available
        _get_balance_bit.return_value = self._get_bittrex_get_balance_response(
            balance, available, pending)
        _get_balance_kraken.return_value = {'result': {'XXDG': str(balance)}}
        _get_card.return_value = {'balance': Decimal(balance),
                                  'available': Decimal(available)}
        account = Account.objects.get(**filters)
        account_balance_checker_invoke.apply_async([account.pk])
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal(str(balance)), name)
        if filters['wallet'] in ['api3', 'api1']:
            self.assertEqual(account.available, Decimal(str(available)), name)
            self.assertEqual(account.pending, Decimal(str(pending)), name)
        elif filters['wallet'] == 'api2':
            self.assertEqual(account.available, Decimal(str(balance)), name)
            self.assertEqual(account.pending, Decimal('0.0'), name)

    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.uphold.Uphold.get_card')
    def test_do_not_update_balance_on_error(self, uphold_get_card,
                                            kraken_private, bittrex_balance,
                                            scrypt_balance):
        uphold_get_card.side_effect = kraken_private.side_effect = \
            bittrex_balance.side_effect = [{}, None]
        scrypt_balance.side_effect = [None, '']
        wallets = ['api1', 'api1', 'api2', 'api2', 'api3', 'api3', 'rpc2',
                   'rpc3']
        balance = available = pending = Decimal('1000.0')
        for wallet in wallets:
            account = Account.objects.filter(wallet=wallet).first()
            account.balance = balance
            account.available = available
            account.pending = pending
            account.save()
            msg = 'account: {}'.format(account)
            account_balance_checker_invoke.apply_async([account.pk])
            account.refresh_from_db()
            self.assertEqual(account.balance, balance, msg)
            self.assertEqual(account.available, available, msg)
            self.assertEqual(account.pending, pending, msg)

    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_reserve_balance_maintainer_buy_xvg(self, _get_balance, get_ticker,
                                                sell_limit, buy_limit):
        balance = self.reserve.min_expected_level - Decimal('1.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance), available=float(balance))
        diff = self.reserve.target_level - balance
        ask = Decimal('0.001')
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask)
        sell_limit.return_value = {'message': 'mock SELL'}
        buy_limit.return_value = {'message': 'mock BUY'}
        reserve_balance_maintainer_invoke.apply_async([self.reserve.pk])
        self.assertEqual(buy_limit.call_count, 1)
        self.assertEqual(sell_limit.call_count, 0)
        buy_limit.assert_called_with(
            'BTC-{}'.format(self.reserve.currency), diff, ask)

    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.get_balance')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    def test_reserve_balance_maintainer_doge(self, q_public, q_private,
                                             rpc_balance, get_ticker):
        rpc_balance.return_value = '0.0'
        reserve = Reserve.objects.get(currency__code='DOGE')
        balance_min = reserve.min_expected_level - Decimal('1.0')
        balance_max = reserve.max_expected_level + Decimal('1.0')
        ask = bid = '0.001'
        self.add_order_params = None
        self.pair_name = None

        def side_public(a, b):
            if a == 'Ticker':
                self.pair_name = b['pair']
                return {
                    'error': [],
                    'result': {self.pair_name: {'a': [ask], 'b': [bid]}}
                }

        def side_private(a, b=None):
            if a == 'Balance':
                return {'result': {'XXDG': str(self.balance)}}
            elif a == 'AddOrder':
                self.add_order_params = b
                return {
                    'result': {'refid': 'AGB25DS-KHKBDX-OHDST7'}, 'error': []
                }
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=Decimal(ask) * Decimal('1.1'),
            bid=Decimal(ask) * Decimal('0.9'),
        )
        q_public.side_effect = side_public
        q_private.side_effect = side_private
        for balance in [balance_min, balance_max]:
            diff = reserve.target_level - balance
            order_type = 'sell' if diff < 0 else 'buy'
            diff = abs(diff)
            self.balance = balance
            reserve_balance_maintainer_invoke.apply_async([reserve.pk])
            self.assertEqual(
                self.add_order_params,
                {'price': ask, 'type': order_type, 'pair': self.pair_name,
                 'ordertype': 'limit', 'volume': str(diff)}
            )

    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_reserve_balance_maintainer_sell_xvg(self, _get_balance,
                                                 get_ticker, sell_limit,
                                                 buy_limit):
        balance = self.reserve.max_expected_level + Decimal('1.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance), available=float(balance))
        diff = balance - self.reserve.target_level
        bid = Decimal('0.001')
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            bid=bid)
        sell_limit.return_value = {'message': 'mock SELL'}
        buy_limit.return_value = {'message': 'mock BUY'}
        reserve_balance_maintainer_invoke.apply_async([self.reserve.pk])
        self.assertEqual(buy_limit.call_count, 0)
        self.assertEqual(sell_limit.call_count, 1)
        sell_limit.assert_called_with(
            'BTC-{}'.format(self.reserve.currency), diff, bid)

    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_reserve_balance_maintainer_none_xvg(self, _get_balance,
                                                 get_ticker, sell_limit,
                                                 buy_limit):
        balance = self.reserve.target_level
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance), available=float(balance))
        sell_limit.return_value = {'message': 'mock SELL'}
        buy_limit.return_value = {'message': 'mock BUY'}
        reserve_balance_maintainer_invoke.apply_async([self.reserve.pk])
        self.assertEqual(buy_limit.call_count, 0)
        self.assertEqual(sell_limit.call_count, 0)
        self.assertEqual(get_ticker.call_count, 0)

    @patch.dict(os.environ, {'RPC3_PUBLIC_KEY_C1': RPC3_PUBLIC_KEY_C1})
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'get_accounts')
    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_fill_main_account_xvg(self, _get_balance, get_ticker,
                                   buy_limit, withdraw, get_accounts,
                                   scrypt_info):
        scrypt_info.return_value = {}
        get_accounts.return_value = [RPC3_PUBLIC_KEY_C1]
        account_from = self.reserve.account_set.get(wallet='api3')
        balance = self.reserve.target_level
        amount = balance * Decimal('2.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance))
        buy_limit.return_value = {'message': 'mock BUY'}
        withdraw.return_value = {'success': True, 'uuid': '12345'}
        ask = Decimal('0.001')
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask)
        main_account_filler_invoke.apply_async([account_from.pk, amount, True])
        self.assertEqual(buy_limit.call_count, 1)
        pair_name = 'BTC-{}'.format(self.reserve.currency.code)
        buy_limit.assert_called_with(pair_name, amount - balance, ask)
        self.assertEqual(get_ticker.call_count, 1)
        self.assertEqual(withdraw.call_count, 1)
        withdraw.assert_called_with(
            self.reserve.currency.code,
            amount,
            RPC3_PUBLIC_KEY_C1
        )

    @patch.dict(os.environ, {'RPC2_PUBLIC_KEY_C1': RPC2_PUBLIC_KEY_C1})
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'get_accounts')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    def test_fill_main_account_doge(self, q_public, q_private, get_accounts,
                                    scrypt_info):
        scrypt_info.return_value = {}
        get_accounts.return_value = [RPC2_PUBLIC_KEY_C1]
        account_from = Account.objects.get(reserve__currency__code='DOGE',
                                           wallet='api2')
        self.balance = account_from.reserve.target_level
        amount = self.balance * Decimal('2')
        ask = bid = '0.001'
        self.add_order_params = self.withdraw_params = None

        def side_public(a, b):
            if a == 'Ticker':
                self.pair_name = b['pair']
                return {
                    'error': [],
                    'result': {self.pair_name: {'a': [ask], 'b': [bid]}}
                }

        def side_private(a, b=None):
            if a == 'Balance':
                return {'result': {'XXDG': str(self.balance)}}
            elif a == 'AddOrder':
                self.add_order_params = b
                return {
                    'result': {'refid': 'AGB25DS-KHKBDX-OHDST7'}, 'error': []
                }
            elif a == 'Withdraw':
                self.withdraw_params = b
                return {
                    'result': {'refid': 'AGB25DS-KHKBDX-OHDST7'}, 'error': []
                }

        q_public.side_effect = side_public
        q_private.side_effect = side_private

        main_account_filler_invoke.apply_async([account_from.pk, amount, True])
        self.assertEqual(
            self.add_order_params,
            {'volume': str(self.balance), 'price': ask,
             'ordertype': 'limit', 'type': 'buy', 'pair': 'XXDGXXBT'}
        )
        self.assertEqual(
            self.withdraw_params,
            {'key': RPC2_PUBLIC_KEY_C1, 'amount': str(amount),
             'asset': 'XXDG'}
        )

    @patch('risk_management.tasks.generic.base.BaseAccountManagerTask.'
           'update_account_balance')
    def test_invoke_task_bad_account_id(self, run):
        account_balance_checker_invoke.apply_async([-1])
        self.assertEqual(run.call_count, 0)

    @patch('risk_management.tasks.generic.base.BaseAccountManagerTask.'
           'send_funds_to_main_account')
    def test_invoke_main_account_filler_bad_account_id(self, run):
        main_account_filler_invoke.apply_async([-1, 1000])
        self.assertEqual(run.call_count, 0)

    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_create_xvg_cover(self, _get_balance, get_ticker, buy_limit,
                              withdraw):
        ask = Decimal('0.0012')
        tx_id = '12345'
        amount_base = Decimal('10000')
        pair = Pair.objects.get(name='XVGBTC')
        _get_balance.return_value = self._get_bittrex_get_balance_response(50)
        buy_limit.return_value = withdraw.return_value = {
            'result': {'uuid': tx_id}
        }
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask)
        currency_cover_invoke.apply(['XVG', amount_base])
        cover = Cover.objects.last()
        self.assertEqual(cover.rate, ask)
        self.assertEqual(cover.amount_base, amount_base)
        self.assertEqual(cover.pair, pair)
        self.assertEqual(cover.currency.code, 'XVG')
        self.assertEqual(cover.amount_quote, ask * amount_base)


class UncoveredTestCase(RiskManagementBaseTestCase):

    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    def test_bittrex_sell_limit_without_rate(self, get_ticker, sell_limit):
        bid = Decimal('0.001')
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            bid=bid)
        client = BittrexApiClient()
        pair = Pair.objects.get(name='XVGBTC')
        amount = 123
        client.sell_limit(pair, 123)
        sell_limit.assert_called_with('BTC-XVG', amount, bid)

    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    def test_bittrex_release_with_objects(self, withdraw):
        client = BittrexApiClient()
        curr_code = 'XVG'
        curr = Currency.objects.get(code=curr_code)
        address_address = '123'
        address = Address(address=address_address, currency=curr,
                          type=Address.WITHDRAW)
        amount = 123
        client.release_coins(curr, address, amount)
        withdraw.assert_called_with(curr_code, amount, address_address)

    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    def test_kraken_sell_limit_without_rate(self, q_public, q_private):
        client = KrakenApiClient()
        bid = '0.001'
        ask = '0.002'

        def side_public(a, b):
            if a == 'Ticker':
                self.pair_name = b['pair']
                return {
                    'error': [],
                    'result': {self.pair_name: {'a': [ask], 'b': [bid]}}
                }
        q_public.side_effect = side_public
        pair = Pair.objects.get(name='DOGEBTC')
        amount = 123
        client.sell_limit(pair, 123)
        q_private.assert_called_with(
            'AddOrder',
            {'pair': 'XXDGXXBT', 'price': bid, 'volume': str(amount),
             'ordertype': 'limit', 'type': 'sell'}
        )

    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    def test_kraken_release_with_objects(self, q_private):
        client = KrakenApiClient()
        curr_code = 'DOGE'
        curr = Currency.objects.get(code=curr_code)
        address_address = '123'
        address = Address(address=address_address, currency=curr,
                          type=Address.WITHDRAW)
        amount = 123
        client.release_coins(curr, address, amount)
        q_private.assert_called_with(
            'Withdraw', {'amount': str(amount), 'asset': 'XXDG',
                         'key': address_address}
        )

    @patch('risk_management.tasks.generic.reserve_balance_checker.'
           'ReserveBalanceChecker.run')
    def test_currency_reserves_updater(self, checker):
        code = 'XVG'
        reserve = Reserve.objects.get(currency__code=code)
        currency_reserve_balance_checker_invoke.apply([code])
        checker.assert_called_with(reserve.pk)


class PnlTaskTestCase(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['BTCLTC', 'LTCBTC', 'ETHBTC', 'ETHLTC',
             'ETHBDG', 'LTCBDG']
        super(PnlTaskTestCase, cls).setUpClass()
        cls.api_client = APIClient()

    def setUp(self):
        super(PnlTaskTestCase, self).setUp()
        self._create_enough_addresses_for_test()
        self._create_orders_for_test()

    def _create_enough_addresses_for_test(self):
        curs = Currency.objects.filter(is_crypto=True)
        for cur in curs:
            for i in range(50):
                card = AddressReserve(currency=cur,
                                      address='{}_{}'.format(cur.code, i))
                card.save()

    def _create_order_api(self, amount_base, pair_name, address):
        order_data = {
            "amount_base": amount_base,
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": address
            }
        }
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json'
        )
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        return order

    def _create_orders_for_test(self):
        some_number = 5
        order_data = [
            (0.1, 'BTCLTC', '17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ'),
            (10, 'LTCBTC', 'LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4'),
            (10, 'ETHBTC', '0x77454e832261aeed81422348efee52d5bd3a3684'),
            (10, 'ETHLTC', '0x77454e832261aeed81422348efee52d5bd3a3684'),
            (1, 'ETHBDG', '0x77454e832261aeed81422348efee52d5bd3a3684'),
            (5, 'LTCBDG', 'LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4'),
        ]
        for data in order_data:
            for i in range(some_number):
                amount, pair_name, address = data
                order = self._create_order_api(amount, pair_name, address)
                order.status = Order.COMPLETED
                order.save()

    def test_pnl_sheet(self):
        calculate_pnls.apply_async()
        pnl_sheet = PNLSheet.objects.last()
        pnls = pnl_sheet.pnl_set.all()
        for curr in ['btc', 'usd', 'eth', 'eur']:
            param = 'pnl_{}'.format(curr)
            expected = sum([getattr(pnl, param) for pnl in pnls])
            actual = getattr(pnl_sheet, param)
            self.assertEqual(expected, actual, param)
        btc_pnls = pnls.filter(pair__quote__code='BTC')
        btc_base_pnls = pnls.filter(pair__base__code='BTC')
        expected_position = sum(
            [pnl.position for pnl in btc_pnls] +
            [pnl.base_position for pnl in btc_base_pnls]
        )
        self.assertEqual(pnl_sheet.positions['BTC'], expected_position)
        pnl_sheet.positions_str
        pnl_sheet.__str__()
        pnl = pnls.last()
        pnl.position_str
        pnl.base_position_str
        pnl.pnl_str


class CurrencyDisablingTestCase(RiskManagementBaseTestCase):
    DISABLE_CURR_TESTS = [disable_currency_quote, disable_currency_base,
                          enable_currency_base, enable_currency_quote]

    def tearDown(self):
        DisabledCurrency.objects.all().delete()
        super(CurrencyDisablingTestCase, self).tearDown()

    @staticmethod
    def apply_tasks():
        for task in CurrencyDisablingTestCase.DISABLE_CURR_TESTS:
            task.apply()

    def make_assertions(self, base_pairs, quote_pairs, expected_state_base,
                        expected_state_quote):
        for pair in quote_pairs:
            self.assertTrue(pair.disabled == expected_state_quote)

        for pair in base_pairs:
            self.assertTrue(pair.disabled == expected_state_base)

    @data_provider(
        lambda: (('LTC', True, False),
                 ('LTC', True, True),
                 ('LTC', False, True),
                 ('LTC', False, False),)
    )
    def test_currency_disable_re_enable(self, currency_code,
                                        disabled_state_quote_initial,
                                        disabled_state_base_initial):
        ltc = Currency.objects.get(code=currency_code)

        # This assumes only one DisabledCurrency of kind exists
        DisabledCurrency.objects.all().delete()

        disabled_curr =\
            DisabledCurrency.objects.create(
                currency=ltc,
                disable_quote=disabled_state_quote_initial,
                disable_base=disabled_state_base_initial
            )

        CurrencyDisablingTestCase.apply_tasks()
        quote_pairs = Pair.objects.filter(quote__code=currency_code)
        base_pairs = Pair.objects.filter(base__code=currency_code)
        self.make_assertions(base_pairs, quote_pairs,
                             disabled_state_base_initial,
                             disabled_state_quote_initial)

        DisabledCurrency.objects.filter(pk=disabled_curr.pk)\
            .update(disable_quote=not disabled_state_quote_initial,
                    disable_base=not disabled_state_base_initial)
        CurrencyDisablingTestCase.apply_tasks()
        quote_pairs = Pair.objects.filter(quote__code=currency_code)
        base_pairs = Pair.objects.filter(base__code=currency_code)
        self.make_assertions(base_pairs, quote_pairs,
                             not disabled_state_base_initial,
                             not disabled_state_quote_initial)

    def test_do_not_enable_if_disabled(self):
        eth = Currency.objects.get(code='ETH')
        nano = Currency.objects.get(code='NANO')
        DisabledCurrency.objects.create(currency=eth)
        DisabledCurrency.objects.create(currency=nano, disable_base=False)

        CurrencyDisablingTestCase.apply_tasks()

        eth_pairs = Pair.objects.filter(quote__code='ETH')

        for pair in eth_pairs:
            self.assertTrue(pair.disabled)
