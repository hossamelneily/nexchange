from core.tests.base import TransactionImportBaseTestCase
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
from core.tests.base import RPC8_PUBLIC_KEY_C1, RPC8_WALLET, \
    RPC8_PORT, RPC8_PASSWORD, RPC8_USER, RPC8_HOST
from risk_management.models import Reserve

RPC11_URL = 'http://{}/json_rpc'.format(RPC8_HOST)
RPC12_PUBLIC_KEY_C1 = '44AFFq5kSiAAaA4AAAaAaA18obc8AemS33DBLWs3H7otXft' \
                      '3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A'


class CryptonightRawE2ETestCase(TransactionImportBaseTestCase,
                                TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['XMRBTC', 'BTCXMR']
        super(CryptonightRawE2ETestCase, cls).setUpClass()
        cls.import_txs_task = import_transaction_deposit_crypto_invoke
        cls.update_confirmation_task = update_pending_transactions_invoke
        cls.api_client = APIClient()

        cls.reserves = Reserve.objects.all()
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=False):
                if account.wallet != 'rpc11':
                    account.disabled = True
                    account.save()

    @classmethod
    def tearDownClass(cls):
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=True):
                account.disabled = False
                account.save()

    def _create_paid_order_api(self, pair_name, amount_base,
                               address, payment_id):
        order_data = {
            "amount_base": amount_base,
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "payment_id": payment_id,
            "withdraw_address": {
                "address": address
            }
        }
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        try:
            order = Order.objects.get(
                unique_reference=response.json()['unique_reference']
            )
        except KeyError:
            return
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
            ('BTCXMR',),
        )
    )
    @patch.dict(os.environ, {'RPC11_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_NAME': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC_RPC11_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC11_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC11_PORT': RPC8_PORT})
    @requests_mock.mock()
    def test_pay_cryptonight_order(self, pair_name, mock):
        amount_base = 0.1
        self._create_order(pair_name=pair_name, amount_base=amount_base)
        mock_currency = self.order.pair.quote
        mock_amount = self.order.amount_quote

        card = self.order.deposit_address.reserve
        current_block = 10
        tx_block_height = 10
        payment_id = self.order.payment_id

        raw_cryptonight_txs = \
            self.get_cryptonight_raw_txs(
                mock_currency, mock_amount, card.address, tx_block_height,
                payment_id
            )

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('method') == 'create_address']):
                return {'id': 0,
                        'jsonrpc': '2.0',
                        'result': {
                            'address': self._get_id('B'),
                            'address_index': 6}
                        }
            if params.get('method') in ['open_wallet', 'store']:
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}
            if params.get('method') == 'get_transfers':
                return raw_cryptonight_txs
            if params.get('method') == 'get_transfer_by_txid':
                return self.get_cryptonight_raw_tx(raw_cryptonight_txs)
            if params.get('method') == 'getheight':
                return {'id': 0, 'jsonrpc': '2.0',
                        'result': {"height": current_block}}

        mock.post(RPC11_URL, json=text_callback)
        self.import_txs_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # Failed status
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # OK status
        current_block = 21
        mock.post(RPC11_URL, json=text_callback)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)

    @data_provider(
        lambda: (
            ('XMRBTC',),
        )
    )
    @patch.dict(os.environ, {'RPC11_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_NAME': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC_RPC11_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC11_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC11_PORT': RPC8_PORT})
    @requests_mock.mock()
    def test_release_cryptonight_order(self, pair_name, mock):
        amount_base = 10
        withdraw_address = \
            '41pLNkSGSJK8pWAG9dd57YcWB82gH5ucHNEPnGt1FBN' \
            '59PrdYqKUGB1SfZxGQPcYcDEbctmpN2kpVbtupm6yCRf16oXkjuY'
        payment_id = '0123456789ABCDEF'
        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address, payment_id)
        with_tx_id = self.generate_txn_id()
        value = amount_base * (10**order.pair.base.decimals)

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params.get('method') == 'transfer':
                return {
                    "id": "0",
                    "jsonrpc": "2.0",
                    "result": {
                        "amount": value,
                        "fee": 939900000,
                        "multisig_txset": "",
                        "tx_hash": with_tx_id,
                        "tx_key": "63e660b49ff678fa6f7f4a103977d96646"
                                  "f4c564c0c37e9bed50d019939cae06",
                    }
                }
            if params.get('method') in ['open_wallet', 'store']:
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}
            if params.get('method') == 'get_transfer_by_txid':
                return {
                    'id': 0,
                    'jsonrpc': '2.0',
                    'result': {
                        'transfer': {
                            'double_spend_seen': False,
                            'height': 10
                        }
                    }
                }
            if params.get('method') in ['getheight', 'get_info']:
                return {'id': 0, 'jsonrpc': '2.0',
                        'result': {"height": 21}}
            if params.get('method') == 'getbalance':
                return {
                    'id': '0',
                    'jsonrpc': '2.0',
                    'result': {
                        'balance': value * 2,
                        'unlocked_balance': value * 2
                    }
                }

        mock.post(RPC11_URL, json=text_callback)
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

    @data_provider(
        lambda: (
            ('0123456789ABCDEF',),
            ('incorrect0123456789ABCDEF',),
            ('01234567incorrect89ABCDEF',),
            ('01234@6789AB*DEF',),
            ('0123456789ABCDEF0123456789ABCDEF0123456789'
             'ABCDEF0123456789ABCDEF',),
            ('incort0123456789ABCDEF0123456789ABCDEF0123'
             '456789ABCDEF0123456789ABCDEF',),
            ('789ABCDEF0123456789ABCDEF0123456789ABCDEF0'
             '123456789ABCDEF',),
            ('',),
        )
    )
    def test_order_creation_dependance_on_payment_id(self, payment_id):
        pair_name = 'XMRBTC'
        amount_base = 1
        withdraw_address = \
            '41pLNkSGSJK8pWAG9dd57YcWB82gH5ucHNEPnGt1FBN' \
            '59PrdYqKUGB1SfZxGQPcYcDEbctmpN2kpVbtupm6yCRf16oXkjuY'

        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address, payment_id)
        if order:
            self.assertEqual(order.withdraw_address.address, withdraw_address)
        else:
            self.assertIsNone(order)
