from core.tests.base import TransactionImportBaseTestCase
from risk_management.models import Reserve
from ticker.tests.base import TickerBaseTestCase
from core.tests.utils import data_provider
from unittest.mock import patch
from accounts.task_summary import import_transaction_deposit_crypto_invoke,\
    update_pending_transactions_invoke
from orders.task_summary import exchange_order_release_periodic
from risk_management.task_summary import reserves_balance_checker_periodic
from orders.models import Order
from core.models import Transaction
import os
from rest_framework.test import APIClient
import requests_mock
import json
from core.tests.base import RPC8_WALLET, RPC8_PUBLIC_KEY_C1, RPC8_PORT, \
    RPC8_HOST, RPC8_USER, RPC8_PASSWORD, RPC8_URL, BLAKE2_ROOT
from accounts import task_summary as account_tasks


class Blake2RawE2ETestCase(TransactionImportBaseTestCase,
                           TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['NANOBTC', 'BTCNANO']
        super(Blake2RawE2ETestCase, cls).setUpClass()
        cls.import_txs_task = import_transaction_deposit_crypto_invoke
        cls.update_confirmation_task = update_pending_transactions_invoke
        cls.api_client = APIClient()

        cls.reserves = Reserve.objects.all()
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=False):
                if account.wallet != 'rpc8':
                    account.disabled = True
                    account.save()

    @classmethod
    def tearDownClass(cls):
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=True):
                account.disabled = False
                account.save()

    def _query_to_dict(self, query):
        res = {}
        params = query.split('&')
        for param in params:
            key_val = param.split('=')
            res.update({key_val[0]: key_val[1]})
        return res

    def _create_paid_order_api(self, pair_name, amount_base, address):
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
            order_api_url, order_data, format='json')
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        tx_data = {
            'amount': order.amount_quote,
            'tx_id': self.generate_txn_id(),
            'order': order,
            'address_to': order.deposit_address,
            'type': Transaction.DEPOSIT,
            'currency': order.pair.quote
        }
        res = order.register_deposit(tx_data)
        tx = res.get('tx')
        order.confirm_deposit(tx)
        return order

    @data_provider(
        lambda: (
            ('BTCNANO',),
        )
    )
    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': RPC8_PORT})
    @patch('core.models.Currency.is_quote_of_enabled_pair')
    @patch('accounts.tasks.monitor_wallets.app.send_task')
    @requests_mock.mock()
    def test_pay_blake2_order(self, pair_name, send_task, is_quote, mock):
        is_quote.return_value = True
        amount_base = 0.5
        self._create_order(pair_name=pair_name, amount_base=amount_base)
        mock_currency = self.order.pair.quote
        mock_amount = self.order.amount_quote

        card = self.order.deposit_address.reserve
        self.pending_exists = '1'

        balance = str(int(mock_amount * (10**mock_currency.decimals)))

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_list',
                    params.get('wallet')]):
                return {'accounts': [self.order.deposit_address.address,
                                     RPC8_PUBLIC_KEY_C1]}
            if all([params.get('action') == 'account_history',
                    params.get('account'), params.get('count')]):
                return self.get_blake2_raw_tx(mock_currency, mock_amount,
                                              card.address)
            if all([params.get('action') == 'pending_exists',
                    params.get('hash')]):
                return {'exists': self.pending_exists}
            if all([params.get('action') == 'account_balance',
                    params.get('account') == card.address]):
                return {'balance': balance, 'pending': '0'}
        mock.post(RPC8_URL, json=text_callback)
        self.import_txs_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # Failed status
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # OK status
        self.pending_exists = '0'
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        task, tx_id = send_task.call_args_list[0][0]
        with patch(BLAKE2_ROOT + 'release_coins') as release_coins:
            getattr(
                account_tasks,
                task.split('accounts.task_summary.')[1]
            ).apply_async(tx_id)
            self.assertEqual(release_coins.call_count, 1, pair_name)
            release_coins.assert_called_with(
                mock_currency,
                RPC8_PUBLIC_KEY_C1,
                mock_amount,
                address_from=card.address
            )

    @data_provider(
        lambda: (
            ('NANOBTC',),
        )
    )
    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': RPC8_PORT})
    @requests_mock.mock()
    @patch(BLAKE2_ROOT + '_list_txs')
    def test_release_blake2_order(self, pair_name, mock,
                                  mock_list_txs):
        mock_list_txs.return_value = []
        amount_base = 10
        withdraw_address = \
            'xrb_1111111111111111111111111111111111111111111111111111hifc8npp'
        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address)
        with_tx_id = self.generate_txn_id()
        value = amount_base * (10**order.pair.base.decimals)

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_balance',
                    params.get('account')]):
                return {'balance': str(value * 2), 'pending': '0'}
            if all([params.get('action') == 'send',
                    params.get('wallet'),
                    params.get('source') == RPC8_PUBLIC_KEY_C1,
                    params.get('destination') == withdraw_address,
                    params.get('amount') == str(value)]):
                return {'block': with_tx_id}
            if all([params.get('action') == 'password_enter',
                    params.get('wallet'), 'password' in params]):
                return {'valid': 1}
            if all([params.get('action') == 'pending_exists',
                    params.get('hash') == with_tx_id]):
                return {'exists': '0'}

        mock.post(RPC8_URL, json=text_callback)
        reserves_balance_checker_periodic.apply()
        self.assertTrue(order.coverable)
        exchange_order_release_periodic.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.RELEASED, pair_name)
        tx_w = order.transactions.get(type='W')
        self.assertEqual(tx_w.tx_id, with_tx_id)
        self.assertEqual(tx_w.amount, order.amount_base)
        self.update_confirmation_task.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.COMPLETED, pair_name)

    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': RPC8_PORT})
    @patch(BLAKE2_ROOT + 'health_check')
    @patch(BLAKE2_ROOT + 'release_coins')
    @requests_mock.mock()
    def test_do_not_release_if_transaction_is_not_unique(self,
                                                         mock_release_coins,
                                                         mock_health_check,
                                                         mock):
        mock_health_check.return_value = True
        amount_base = 10
        withdraw_address = \
            'xrb_1111111111111111111111111111111111111111111111111111hifc8npp'
        order = self._create_paid_order_api('NANOBTC', amount_base,
                                            withdraw_address)
        NANO = order.pair.base

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_list',
                    params.get('wallet')]):
                return {'accounts': [order.deposit_address.address,
                                     RPC8_PUBLIC_KEY_C1]}
            if all([params.get('action') == 'account_history',
                    params.get('account'), params.get('count')]):
                return self.get_blake2_raw_tx_send(
                    NANO, order.amount_base, withdraw_address
                )

        mock.post(RPC8_URL, json=text_callback)
        exchange_order_release_periodic.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PRE_RELEASE)
        self.assertTrue(order.flagged, True)
        self.assertEqual(mock_release_coins.call_count, 0)
