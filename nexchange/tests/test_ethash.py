from unittest import TestCase
from nexchange.api_clients.rpc import EthashRpcApiClient
from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from core.tests.utils import data_provider
from unittest.mock import patch
from core.tests.base import ETH_ROOT
from accounts.task_summary import import_transaction_deposit_crypto_invoke,\
    update_pending_transactions_invoke
from orders.task_summary import exchange_order_release_periodic
from risk_management.task_summary import reserves_balance_checker_periodic
from orders.models import Order
from core.models import Transaction, Currency, Pair
import os
from rest_framework.test import APIClient
from accounts import task_summary as account_tasks
from django.conf import settings
from decimal import Decimal
from collections import namedtuple


ethash_check_tx_params = namedtuple(
    'eth_check_tx_params',
    ['case_name', 'tx_block', 'current_block', 'tx_status', 'min_confs',
     'expected_return']
)


class EthashClientTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(EthashClientTestCase, self).__init__(*args, **kwargs)
        self.client = EthashRpcApiClient()

    def test_data_hash(self):
        address = '0x74f6fcffac8cbf168684892837f27877e20c9e66'
        value = int(100 * 1e18)
        data_expected = \
            '0xa9059cbb' \
            '00000000000000000000000074f6fcffac8cbf168684892837f27877e20c9e66'\
            '0000000000000000000000000000000000000000000000056bc75e2d63100000'
        data = self.client.get_data_hash(
            'transfer(address,uint256)',
            *[address, hex(value)]
        )
        self.assertEqual(data_expected, data)


class EthashRawE2ETestCase(TransactionImportBaseTestCase,
                           TickerBaseTestCase):

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['BTCETH', 'BTCBDG', 'BTCEOS', 'BTCOMG',
                                     'ETHBTC', 'BDGBTC', 'EOSBTC', 'OMGBTC']
        super(EthashRawE2ETestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.api_client = APIClient()
        self.api = EthashRpcApiClient()

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
            ('BTCETH',),
            ('BTCBDG',),
            ('BTCEOS',),
            ('BTCOMG',),
        )
    )
    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': '0xmain_card'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch('core.models.Currency.is_quote_of_enabled_pair')
    @patch('accounts.tasks.monitor_wallets.app.send_task')
    @patch(ETH_ROOT + 'get_accounts')
    @patch('web3.eth.Eth.getTransactionReceipt')
    @patch('web3.eth.Eth.blockNumber')
    @patch('web3.eth.Eth.getTransaction')
    @patch('web3.eth.Eth.getBlock')
    def test_pay_ethash_order(self, pair_name,
                              get_txs_eth_raw, get_tx_eth,
                              get_block_eth, get_tx_eth_receipt, get_accounts,
                              send_task, is_quote):
        is_quote.return_value = True
        amount_base = 0.5
        self._create_order(pair_name=pair_name, amount_base=amount_base)
        mock_currency = self.order.pair.quote
        mock_amount = self.order.amount_quote

        card = self.order.deposit_address.reserve
        get_accounts.return_value = [card.address.upper()]

        get_txs_eth_raw.return_value = self.get_ethash_block_raw(
            mock_currency, mock_amount, card.address
        )
        confs = mock_currency.min_confirmations + 1
        get_tx_eth.return_value = self.get_ethash_tx_raw(
            mock_currency, mock_amount, card.address, block_number=0
        )
        get_block_eth.return_value = confs
        self.import_txs_task.apply()

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # Failed status
        get_tx_eth_receipt.return_value = self.get_ethash_tx_receipt_raw(
            mock_currency, mock_amount, status=0, _to=card.address
        )
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        # Success status
        get_tx_eth_receipt.return_value = self.get_ethash_tx_receipt_raw(
            mock_currency, mock_amount, status=1, _to=card.address
        )
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        # Check Send Gas
        task, tx_id = send_task.call_args[0]
        with patch(ETH_ROOT + 'release_coins') as release_coins:
            getattr(
                account_tasks,
                task.split('accounts.task_summary.')[1]
            ).apply_async(tx_id)
            if mock_currency.is_token:
                self.assertEqual(release_coins.call_count, 1, pair_name)
                release_coins.assert_called_with(
                    Currency.objects.get(code='ETH'),
                    card.address,
                    Decimal(
                        str(settings.RPC_GAS_LIMIT_TOKEN * settings.RPC_GAS_PRICE / (10**18))  # noqa
                    )
                )
            else:
                self.assertEqual(release_coins.call_count, 0, pair_name)

    @data_provider(
        lambda: (
            ('ETHBTC',),
            ('BDGBTC',),
            ('EOSBTC',),
            ('OMGBTC',),
        )
    )
    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': '0xmain_card'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch(ETH_ROOT + 'net_listening')
    @patch('web3.eth.Eth.call')
    @patch('web3.eth.Eth.getTransactionReceipt')
    @patch('web3.eth.Eth.blockNumber')
    @patch('web3.eth.Eth.getTransaction')
    @patch('web3.eth.Eth.sendTransaction')
    @patch('web3.personal.Personal.lockAccount')
    @patch('web3.personal.Personal.unlockAccount')
    @patch('web3.eth.Eth.getBalance')
    def test_release_ethash_order(self, pair_name, get_balance, unlock, lock,
                                  send_tx, get_tx_eth, get_block_eth,
                                  get_tx_eth_receipt, eth_call, eth_listen):
        eth_listen.return_value = True
        amount_base = 50
        pair = Pair.objects.get(name=pair_name)
        base = pair.base
        if base.minimal_amount >= Decimal(amount_base):
            base.minimal_amount = Decimal(amount_base) / Decimal('2')
            base.save()
        order = self._create_paid_order_api(
            pair_name, amount_base,
            '0x77454e832261aeed81422348efee52d5bd3a3684'
        )
        value = 2 * amount_base * (10**order.pair.base.decimals)
        get_balance.return_value = value
        eth_call.return_value = hex(value)
        reserves_balance_checker_periodic.apply()
        send_tx.return_value = self.generate_txn_id()
        exchange_order_release_periodic.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.RELEASED, pair_name)
        get_tx_eth_receipt.return_value = self.get_ethash_tx_receipt_raw(
            order.pair.base, order.amount_base, status=1,
            _to=order.withdraw_address.address
        )
        confs = order.pair.base.min_confirmations + 1
        get_tx_eth.return_value = self.get_ethash_tx_raw(
            order.pair.base, order.amount_base,
            order.withdraw_address.address,
            block_number=0
        )
        get_block_eth.return_value = confs
        self.update_confirmation_task.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.COMPLETED, pair_name)

    @data_provider(lambda: (
        ethash_check_tx_params(
            case_name='Min Confirmation, confirmed',
            tx_block=0, current_block=12, tx_status=1, min_confs=12,
            expected_return=(True, 12)
        ),
        ethash_check_tx_params(
            case_name='1 Confirmation, not confirmed',
            tx_block=0, current_block=1, tx_status=1, min_confs=12,
            expected_return=(False, 1)
        ),
        ethash_check_tx_params(
            case_name='Min confirmations 0, not confirmed',
            tx_block=0, current_block=0, tx_status=1, min_confs=0,
            expected_return=(False, 0)
        ),
        ethash_check_tx_params(
            case_name='Min confirmations with bad status, not confirmed',
            tx_block=0, current_block=12, tx_status=0, min_confs=12,
            expected_return=(False, 12)
        ),
    ))
    @patch(ETH_ROOT + '_get_current_block')
    @patch(ETH_ROOT + '_get_tx_receipt')
    @patch(ETH_ROOT + '_get_tx')
    def test_check_tx_ethash(self, get_tx, get_tx_receipt, get_current_block,
                             **kwargs):
        tx_id = '123'
        self.ETH.min_confirmations = kwargs['min_confs']
        self.ETH.save()
        get_tx.return_value = self.get_ethash_tx_raw(
            self.ETH, Decimal('1'), '0x', block_number=kwargs['tx_block']
        )
        get_tx_receipt.return_value = self.get_ethash_tx_receipt_raw(
            self.ETH, Decimal('1'), status=kwargs['tx_status']
        )
        get_current_block.return_value = kwargs['current_block']
        res = self.api.check_tx(tx_id, self.ETH)
        self.assertEqual(res, kwargs['expected_return'], kwargs['case_name'])
