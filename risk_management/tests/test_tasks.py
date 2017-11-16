from risk_management.tests.base import RiskManagementBaseTestCase
from unittest.mock import patch
from risk_management.task_summary import reserves_balance_checker_periodic,\
    account_balance_checker_invoke, reserve_balance_maintainer_invoke,\
    main_account_filler_invoke, currency_reserve_balance_checker_invoke, \
    currency_cover_invoke
from risk_management.models import Reserve, Account, Cover
from decimal import Decimal
from django.conf import settings
from core.tests.utils import data_provider
from core.models import Pair, Currency, Address
from nexchange.api_clients.kraken import KrakenApiClient
from nexchange.api_clients.bittrex import BittrexApiClient
from core.tests.base import ETH_ROOT, SCRYPT_ROOT


class BalanceTaskTestCase(RiskManagementBaseTestCase):

    def setUp(self):
        super(BalanceTaskTestCase, self).setUp()
        self.reserve = Reserve.objects.get(currency__code='XVG')

    @patch('nexchange.api_clients.uphold.Uphold.get_card')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch(SCRYPT_ROOT + 'get_balance')
    @patch(ETH_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_check_all_reserves_balances(self, get_balance_bit,
                                         get_balance_eth, get_balance_rpc,
                                         get_balance_kraken,
                                         get_card):
        balance = 800.0
        available = 500.0
        pending = balance - available
        get_balance_bit.return_value = self._get_bittrex_get_balance_response(
            balance, available, pending)
        get_balance_rpc.return_value = get_balance_eth.return_value = Decimal(
            str(balance)
        )
        get_balance_kraken.return_value = {'result': {'XXDG': str(balance)}}
        get_card.return_value = {'balance': Decimal(balance),
                                 'available': Decimal(available)}
        reserves_balance_checker_periodic.apply_async()
        reserves = Reserve.objects.all()
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
        balance = self.reserve.min_expected_balance - Decimal('1.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance))
        diff = self.reserve.expected_balance - balance
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

    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.get_balance')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    def test_reserve_balance_maintainer_doge(self, q_public, q_private,
                                             rpc_balance):
        rpc_balance.return_value = '0.0'
        reserve = Reserve.objects.get(currency__code='DOGE')
        balance_min = reserve.min_expected_balance - Decimal('1.0')
        balance_max = reserve.max_expected_balance + Decimal('1.0')
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
        q_public.side_effect = side_public
        q_private.side_effect = side_private
        for balance in [balance_min, balance_max]:
            diff = reserve.expected_balance - balance
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
        balance = self.reserve.max_expected_balance + Decimal('1.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance))
        diff = balance - self.reserve.expected_balance
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
        balance = self.reserve.expected_balance
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance))
        sell_limit.return_value = {'message': 'mock SELL'}
        buy_limit.return_value = {'message': 'mock BUY'}
        reserve_balance_maintainer_invoke.apply_async([self.reserve.pk])
        self.assertEqual(buy_limit.call_count, 0)
        self.assertEqual(sell_limit.call_count, 0)
        self.assertEqual(get_ticker.call_count, 0)

    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_fill_main_account_xvg(self, _get_balance, get_ticker,
                                   buy_limit, withdraw):
        account_from = self.reserve.account_set.get(wallet='api3')
        balance = self.reserve.expected_balance
        amount = balance * Decimal('2.0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance))
        buy_limit.return_value = {'message': 'mock BUY'}
        withdraw.return_value = {'success': True, 'uuid': '12345'}
        ask = Decimal('0.001')
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask)
        main_account_filler_invoke.apply_async([account_from.pk, amount])
        self.assertEqual(buy_limit.call_count, 1)
        pair_name = 'BTC-{}'.format(self.reserve.currency.code)
        buy_limit.assert_called_with(pair_name, amount - balance, ask)
        self.assertEqual(get_ticker.call_count, 1)
        self.assertEqual(withdraw.call_count, 1)
        withdraw.assert_called_with(
            self.reserve.currency.code,
            amount,
            settings.API3_PUBLIC_KEY_C1
        )

    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    def test_fill_main_account_doge(self, q_public, q_private):
        account_from = Account.objects.get(reserve__currency__code='DOGE',
                                           wallet='api2')
        self.balance = account_from.reserve.expected_balance
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

        main_account_filler_invoke.apply_async([account_from.pk, amount])
        self.assertEqual(
            self.add_order_params,
            {'volume': str(self.balance), 'price': ask,
             'ordertype': 'limit', 'type': 'buy', 'pair': 'XXDGXXBT'}
        )
        self.assertEqual(
            self.withdraw_params,
            {'key': settings.RPC2_PUBLIC_KEY_C1, 'amount': str(amount),
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
