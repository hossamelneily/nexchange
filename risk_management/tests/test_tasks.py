from risk_management.tests.base import RiskManagementBaseTestCase
from unittest.mock import patch
from risk_management.task_summary import reserves_balance_checker_periodic,\
    account_balance_checker_invoke, reserve_balance_maintainer_invoke,\
    main_account_filler_invoke
from risk_management.models import Reserve, Account
from decimal import Decimal
from django.conf import settings


class BalanceTaskTestCase(RiskManagementBaseTestCase):

    def setUp(self):
        super(BalanceTaskTestCase, self).setUp()
        self.reserve = Reserve.objects.get(currency__code='XVG')

    def _get_bittrex_get_balance_response(self, balance, available=None,
                                          pending=None):
        if available is None:
            available = balance * 0.7
        if pending is None:
            pending = balance * 0.3
        response = {
            'result': {
                'Available': available,
                'Balance': balance,
                'CryptoAddress': 'D8BVYkdLYJozKYURTghmgEKRwHm6tYmLn7',
                'Currency': 'XVG',
                'Pending': pending
            },
            'success': True
        }
        return response

    def _get_bittrex_get_ticker_response(self, ask=None, bid=None, last=None):
        response = {
            'success': True,
            'message': '',
            'result': {
                'Last': 1.07e-06 if last is None else last,
                'Ask': 1.08e-06 if ask is None else ask,
                'Bid': 1.07e-06 if bid is None else bid
            }
        }
        return response

    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_check_all_reserves_balances(self, get_balance_bit,
                                         get_balance_rpc):
        pending = 300.0
        balance = 800.0
        available = 500.0
        get_balance_bit.return_value = self._get_bittrex_get_balance_response(
            balance, available, pending)
        get_balance_rpc.return_value = Decimal(str(balance))
        reserves_balance_checker_periodic.apply_async()
        accounts = self.reserve.account_set.all()
        all_balance = all_pending = all_available = Decimal('0')
        for account in accounts:
            self.assertEqual(account.balance, Decimal(str(balance)))
            if account.wallet in ['api3']:
                self.assertEqual(account.available, Decimal(str(available)))
                self.assertEqual(account.pending, Decimal(str(pending)))
            else:
                self.assertEqual(account.available, Decimal(str(balance)))
                self.assertEqual(account.pending, Decimal('0'))
            all_balance += account.balance
            all_available += account.available
            all_pending += account.pending

        self.assertEqual(self.reserve.balance, all_balance)
        self.assertEqual(self.reserve.available, all_available)
        self.assertEqual(self.reserve.pending, all_pending)

    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_check_account_balance(self, _get_balance):
        pending = 300.0
        balance = 800.0
        available = 500.0
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            balance, available, pending)
        account = Account.objects.first()
        account_balance_checker_invoke.apply_async([account.pk])
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal(str(balance)))
        self.assertEqual(account.available, Decimal(str(available)))
        self.assertEqual(account.pending, Decimal(str(pending)))

    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_reserve_balance_maintainer_buy(self, _get_balance, get_ticker,
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

    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_reserve_balance_maintainer_sell(self, _get_balance, get_ticker,
                                             sell_limit, buy_limit):
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
    def test_reserve_balance_maintainer_none(self, _get_balance, get_ticker,
                                             sell_limit, buy_limit):
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
    def test_fill_main_account(self, _get_balance, get_ticker,
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
            settings.API3_ADDR_XVG
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
