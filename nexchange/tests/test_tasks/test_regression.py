from random import randint
from time import time

from unittest.mock import patch

from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke
from core.tests.base import TransactionImportBaseTestCase
from core.tests.base import UPHOLD_ROOT
from core.tests.utils import data_provider
from orders.models import Order
from orders.task_summary import exchange_order_release_invoke, \
    exchange_order_release_periodic
from ticker.tests.base import TickerBaseTestCase


class RegressionTaskTestCase(TransactionImportBaseTestCase,
                             TickerBaseTestCase):

    def setUp(self):
        super(RegressionTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.release_task = exchange_order_release_invoke
        self.release_task_periodic = exchange_order_release_periodic

    @data_provider(
        lambda: (
            ('1.Bad status and confs uphold, cnfs+', 'BTCETH', True,
             (False, 0), Order.PAID),
            ('2.Bad status and confs uphold, cnfs-', 'ETHBTC', False,
             (False, 1), Order.PAID_UNCONFIRMED),
            ('3.Bad status uphold, cnfs+', 'LTCETH', True, (False, 99),
             Order.PAID),
            ('4.Uphold OK, cnfs+', 'BTCLTC', True, (True, 99), Order.PAID),
            ('5.Uphold OK, cnfs-', 'BTCETH', False, (True, 99), Order.PAID),
            ('6.Uphold None, cnfs+', 'BTCETH', False, (None, None),
             Order.PAID_UNCONFIRMED),
        )
    )
    @patch('accounts.tasks.monitor_wallets.check_transaction_blockchain')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_confirmation_with_blockchain(self, name, pair_name, enough_confs,
                                          uphold_checker, last_order_status,
                                          check_tx_uphold,
                                          get_txs_uphold,
                                          prepare_txn_uphold,
                                          execute_txn_uphold,
                                          check_transaction_blockchain):
        currency_quote_code = pair_name[3:]
        amount_base = 11.11
        self._create_order(pair_name=pair_name,
                           amount_base=amount_base)
        mock_currency_code = currency_quote_code
        mock_amount = self.order.amount_quote

        card = self.order.deposit_address.reserve

        card_id = card.card_id
        get_txs_uphold.return_value = [
            self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
        ]
        check_tx_uphold.return_value = uphold_checker
        blockchain_confirmations = self.order.pair.quote.min_confirmations
        if not enough_confs:
            blockchain_confirmations -= 1
        check_transaction_blockchain.return_value = blockchain_confirmations
        self.import_txs_task.apply()
        prepare_txn_uphold.return_value = 'txid_{}{}'.format(
            time(), randint(1, 999))
        execute_txn_uphold.return_value = True

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, last_order_status, name)
        if last_order_status == Order.PAID and 'Uphold OK' not in name:
            txn = self.order.transactions.first()
            self.assertEqual(txn.confirmations, blockchain_confirmations, name)
