from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from core.tests.utils import data_provider
from unittest.mock import patch
from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke
from orders.task_summary import exchange_order_release_periodic
from risk_management.task_summary import reserves_balance_checker_periodic
from orders.models import Order
from core.models import Transaction
import os
from rest_framework.test import APIClient
import requests_mock
import json
from core.tests.base import RPC8_PORT, RPC8_PASSWORD, RPC8_USER, RPC8_HOST, \
    RIPPLE_ROOT
from risk_management.models import Reserve

RPC13_PUBLIC_KEY_C1 = 'rnErCcvuHdxfUEcU81NtujYv36mQ4BaSP2'
RPC13_URL = 'http://{}:{}@{}'.format(RPC8_USER, RPC8_PASSWORD, RPC8_HOST)


class RippleRawE2ETestCase(TransactionImportBaseTestCase,
                           TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['XRPBTC', 'BTCXRP']
        super(RippleRawE2ETestCase, cls).setUpClass()
        cls.import_txs_task = import_transaction_deposit_crypto_invoke
        cls.update_confirmation_task = update_pending_transactions_invoke
        cls.api_client = APIClient()

        cls.reserves = Reserve.objects.all()
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=False):
                if account.wallet != 'rpc13':
                    account.disabled = True
                    account.save()

    @classmethod
    def tearDownClass(cls):
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=True):
                account.disabled = False
                account.save()

    def _create_paid_order_api(self, pair_name, amount_base,
                               address, dest_tag=None):
        order_data = {
            "amount_base": str(amount_base),
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": address
            }
        }
        if dest_tag is not None:
            order_data["destination_tag"] = dest_tag
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
        if dest_tag is not None:
            tx_data["destination_tag"] = dest_tag
        res = order.register_deposit(tx_data)
        tx = res.get('tx')
        order.confirm_deposit(tx)
        return order

    @data_provider(
        lambda: (
                ('123456',),
                ('2222',),
                ('123456',),
                (None,),
        )
    )
    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': RPC13_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': RPC8_PORT})
    @requests_mock.mock()
    def test_pay_ripple_order(self, tx_tag, mock):
        pair_name = 'BTCXRP'
        amount_base = 0.1
        self._create_order(pair_name=pair_name, amount_base=amount_base)

        mock_currency = self.order.pair.quote
        mock_amount = self.order.amount_quote
        raw_amount = str(int(mock_amount * (10 ** mock_currency.decimals)))
        card = self.order.deposit_address.reserve

        tx_id = self.generate_txn_id()
        dest_tag = self.order.destination_tag
        address_to = card.address

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params.get('method') == 'account_tx':
                return self.get_ripple_raw_txs(
                    raw_amount, address_to, tx_tag, tx_id
                )
            if params.get('method') == 'tx':
                return self.get_ripple_raw_tx(
                    raw_amount, address_to, tx_tag, tx_id
                )
        mock.post(RPC13_URL, json=text_callback)
        self.import_txs_task.apply()
        self.order.refresh_from_db()
        if dest_tag == tx_tag:
            self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED,
                              '{} pair order destination tags are: '
                              'order: {} and tx: {}'.format(
                                  pair_name, dest_tag, tx_tag
                              ))
            # OK status
            self.update_confirmation_task.apply()
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, Order.PAID, pair_name)
        else:
            self.assertNotEquals(
                self.order.status, Order.PAID_UNCONFIRMED,
                '{} pair order destination tags are: '
                'order: {} and tx: {}'.format(
                    pair_name, dest_tag, tx_tag
                ))

    @data_provider(
        lambda: (
            ('XRPBTC',),
        )
    )
    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': RPC13_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': RPC8_PORT})
    @requests_mock.mock()
    @patch(RIPPLE_ROOT + '_list_txs')
    def test_release_ripple_order(self, pair_name, mock, mock_list_txs):
        mock_list_txs.return_value = []
        amount_base = 10
        withdraw_address = 'r9y63YwVUQtTWHtwcmYc1Epa5KvstfUzSm'
        dest_tag = '123456'
        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address, dest_tag)

        with_tx_id = self.generate_txn_id()
        value = amount_base * (10**order.pair.base.decimals)
        card_address = RPC13_PUBLIC_KEY_C1

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params.get('method') == 'account_info':
                return {'result': {'account_data': {
                    'Account': card_address,
                    'Balance': '16730415294',
                },
                    'status': 'success',
                    'validated': False
                }}
            if params.get('method') == 'ledger':
                return {'result': {'closed': {'status': 'success'}}}
            if params.get('method') == 'sign':
                return self.get_ripple_sign_response(
                    card_address, value, withdraw_address,
                    dest_tag, with_tx_id
                )
            if params.get('method') == 'submit':
                sign_resp = self.get_ripple_sign_response(
                    card_address, value, withdraw_address,
                    dest_tag, with_tx_id
                )
                sign_resp['result']['engine_result'] = 'tesSUCCESS'
                return sign_resp
            if params.get('method') == 'tx':
                return self.get_ripple_raw_tx(
                    value, withdraw_address, dest_tag, with_tx_id
                )

        mock.post(RPC13_URL, json=text_callback)
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
            ('0000011123',),
            ('143425833',),
            ('0123456789ABCDEF0123456789ABCDEF0123456789'
             'ABCDEF0123456789ABCDEF',),
            ('2**32',),
            ('22657823465782369823657247283926587235325345',),
            ('',),
        )
    )
    def test_order_creation_dependance_on_dest_tag(self, dest_tag):
        pair_name = 'XRPBTC'
        amount_base = 10
        withdraw_address = 'btc_address_123'

        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address, dest_tag)
        if order:
            self.assertEqual(order.withdraw_address.address, withdraw_address)
        else:
            self.assertIsNone(order)

    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': RPC13_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': RPC8_PORT})
    @patch(RIPPLE_ROOT + 'health_check')
    @patch(RIPPLE_ROOT + 'release_coins')
    @requests_mock.mock()
    def test_do_not_release_if_transaction_is_not_unique(self,
                                                         mock_release_coins,
                                                         mock_health_check,
                                                         mock):
        mock_health_check.return_value = True
        withdraw_address = 'r9y63YwVUQtTWHtwcmYc1Epa5KvstfUzSm'
        dest_tag = '123456'

        order = self._create_paid_order_api('XRPBTC', 10, withdraw_address,
                                            dest_tag)
        raw_amount = str(
            int(order.amount_base * (10 ** order.pair.base.decimals))
        )
        tx_id = self.generate_txn_id()

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params.get('method') == 'account_tx':
                return self.get_ripple_raw_txs(
                    raw_amount, withdraw_address, dest_tag, tx_id
                )
            if params.get('method') == 'ledger':
                return {'result': {'closed': {'status': 'success'}}}

        mock.post(RPC13_URL, json=text_callback)
        exchange_order_release_periodic()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PRE_RELEASE)
        self.assertTrue(order.flagged, True)
        self.assertEqual(mock_release_coins.call_count, 0)
