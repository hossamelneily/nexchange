from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from core.tests.utils import data_provider
from unittest.mock import patch
from accounts.task_summary import import_transaction_deposit_crypto_invoke,\
    update_pending_transactions_invoke
from orders.task_summary import exchange_order_release_periodic
from risk_management.task_summary import reserves_balance_checker_periodic
from orders.models import Order, Currency
from core.models import Transaction
import os
from rest_framework.test import APIClient
from core.tests.base import OMNI_ROOT
from nexchange.api_clients.factory import ApiClientFactory
from collections import namedtuple
from risk_management.models import Reserve

RPC10_PASSWORD = 'password'
RPC10_K = 'password'
RPC10_USER = 'user'
RPC10_HOST = '0.0.0.0'
RPC10_PORT = '0000'
RPC10_URL = 'http://{}:{}@{}/'.format(RPC10_USER, RPC10_PASSWORD, RPC10_HOST)

omni_check_tx_params = namedtuple(
    'omni_check_tx_params',
    ['case_name', 'tx_count', 'min_confs',
     'expected_return', 'propertyid', 'type_int',
     'valid']
)

omni_parse_tx_params = namedtuple(
    'omni_parse_tx_params',
    ['property_id', 'tx_id', 'type_int']
)


class OmniRawE2ETestCase(TransactionImportBaseTestCase,
                         TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['USDTBTC', 'BTCUSDT']
        super(OmniRawE2ETestCase, cls).setUpClass()
        cls.import_txs_task = import_transaction_deposit_crypto_invoke
        cls.update_confirmation_task = update_pending_transactions_invoke
        cls.factory = ApiClientFactory()
        cls.api_client = APIClient()
        cls.USDT = Currency.objects.get(code='USDT')

        cls.reserves = Reserve.objects.all()
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=False):
                if account.wallet != 'rpc10':
                    account.disabled = True
                    account.save()

    @classmethod
    def tearDownClass(cls):
        for r in cls.reserves:
            for account in r.account_set.filter(disabled=True):
                account.disabled = False
                account.save()

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
            omni_check_tx_params(
                case_name='Too less confirmations, not confirmed',
                tx_count=1,
                min_confs=12,
                expected_return=(False, 1),
                propertyid=31,
                type_int=0,
                valid=True
            ),
            omni_check_tx_params(
                case_name='Everything passes, confirmed',
                tx_count=6, min_confs=6,
                expected_return=(True, 6),
                propertyid=31,
                type_int=0,
                valid=True
            ),
            omni_check_tx_params(
                case_name='Min Confirmations 0, not confirmed',
                tx_count=0, min_confs=0,
                expected_return=(False, 0),
                propertyid=31,
                type_int=0,
                valid=True
            ),
            omni_check_tx_params(
                case_name='Wrong type, not confirmed',
                tx_count=7, min_confs=6,
                expected_return=(False, 7),
                propertyid=0,
                type_int=1,
                valid=True
            ),
            omni_check_tx_params(
                case_name='Not valid, not confirmed',
                tx_count=7, min_confs=6,
                expected_return=(False, 7),
                propertyid=31,
                type_int=1,
                valid=False
            ),
        )
    )
    @patch(OMNI_ROOT + '_get_tx')
    def test_check_tx_omni(self, mock_get_tx, **kwargs):
        tx = Transaction(tx_id='123')
        self.USDT.min_confirmations = kwargs['min_confs']
        self.USDT.save()
        api = self.factory.get_api_client(self.USDT.wallet)
        mock_get_tx.return_value = {'confirmations': kwargs['tx_count'],
                                    'propertyid': kwargs['propertyid'],
                                    'type_int': kwargs['type_int'],
                                    'valid': kwargs['valid']}
        res = api.check_tx(tx, self.USDT)
        self.assertEqual(res, kwargs['expected_return'], kwargs['case_name'])

    @data_provider(
        lambda: (
            ('BTCUSDT',),
        )
    )
    @patch.dict(os.environ, {'RPC10_PUBLIC_KEY_C1': 'main_address'})
    @patch.dict(os.environ, {'RPC_RPC10_PASSWORD': RPC10_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC10_K': RPC10_K})
    @patch.dict(os.environ, {'RPC_RPC10_USER': RPC10_USER})
    @patch.dict(os.environ, {'RPC_RPC10_HOST': RPC10_HOST})
    @patch.dict(os.environ, {'RPC_RPC10_PORT': RPC10_PORT})
    @patch('core.models.Currency.is_quote_of_enabled_pair')
    @patch(OMNI_ROOT + '_get_tx')
    @patch(OMNI_ROOT + '_get_txs')
    def test_pay_omni_order(self, pair_name, mock_get_txs,
                            mock_get_tx, is_quote):
        is_quote.return_value = True
        amount_base = 0.5
        self._create_order(pair_name=pair_name, amount_base=amount_base)
        mock_amount = self.order.amount_quote

        card = self.order.deposit_address.reserve
        mock_get_txs.return_value = \
            self.get_omni_tx(mock_amount, card.address)
        mock_get_tx.return_value = \
            self.get_omni_tx_raw_unconfirmed(mock_amount, card.address)

        self.import_txs_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # Failed status
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # OK status
        mock_get_txs.return_value = \
            self.get_omni_tx_raw_confirmed(mock_get_tx.return_value)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)

    @data_provider(
        lambda: (
            ('USDTBTC',),
        )
    )
    @patch.dict(os.environ, {'RPC10_PUBLIC_KEY_C1': 'main_address'})
    @patch.dict(os.environ, {'RPC_RPC10_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC10_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC10_USER': 'user'})
    @patch.dict(os.environ, {'RPC_RPC10_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC10_PORT': '0000'})
    @patch(OMNI_ROOT + '_get_tx')
    @patch(OMNI_ROOT + '_get_txs')
    @patch(OMNI_ROOT + 'get_balance')
    @patch(OMNI_ROOT + 'release_coins')
    @patch(OMNI_ROOT + 'health_check')
    @patch('orders.models.Order._validate_order_amount')
    @patch('orders.models.Order.coverable')
    def test_release_omni_order(self, pair_name, is_coverable,
                                mock_validate_order_amount,
                                mock_health_check, mock_release_coins,
                                mock_get_balance, mock_get_txs, mock_get_tx):
        mock_health_check.return_value = True
        is_coverable.return_value = True
        mock_validate_order_amount.start()
        amount_base = 10
        with_tx_id = self.generate_txn_id()
        mock_release_coins.return_value = with_tx_id, True
        withdraw_address = \
            '1AnjHn7L7X4di46HF9Sxm7T7fKEkwqefvb'
        order = self._create_paid_order_api(pair_name, amount_base,
                                            withdraw_address)
        mock_get_balance.return_value = {
            "balance": "100.00000000",
            "ulocked_balance": "100.00000000"
        }
        mock_amount = self.order.amount_quote

        mock_get_tx.return_value = \
            self.get_omni_tx_raw_unconfirmed(mock_amount, 'random_address')
        mock_get_txs.return_value = \
            self.get_omni_tx_raw_confirmed(mock_get_tx.return_value)

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
        mock_validate_order_amount.stop()
