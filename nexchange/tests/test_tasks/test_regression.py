from unittest.mock import patch

from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke, \
    import_transaction_deposit_uphold_blockchain_invoke
from core.tests.base import TransactionImportBaseTestCase
from core.tests.base import UPHOLD_ROOT, EXCHANGE_ORDER_RELEASE_ROOT
from core.tests.utils import data_provider
from core.models import Transaction, Pair, Address
from orders.models import Order
from orders.task_summary import exchange_order_release_invoke
from ticker.tests.base import TickerBaseTestCase
from decimal import Decimal
from unittest import skip


class RegressionTaskTestCase(TransactionImportBaseTestCase,
                             TickerBaseTestCase):

    def setUp(self):
        super(RegressionTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.import_txs_blockchain_task = \
            import_transaction_deposit_uphold_blockchain_invoke
        self.update_confirmation_task = update_pending_transactions_invoke

    def _create_PAID_order(self, txn_type=Transaction.DEPOSIT):
        self._create_order()
        deposit_tx_id = self.generate_txn_id()
        txn_dep = Transaction(
            amount=self.order.amount_quote,
            tx_id_api=deposit_tx_id, order=self.order,
            address_to=self.order.deposit_address,
            is_completed=True,
            is_verified=True
        )
        if txn_type is not None:
            txn_dep.type = txn_type
        txn_dep.save()
        withdraw_address = Address.objects.filter(
            type=Address.WITHDRAW, currency=self.order.pair.base).first()
        self.order.status = Order.PAID
        self.order.withdraw_address = withdraw_address
        self.order.save()
        return self.order, txn_dep

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
        currency_quote_code = Pair.objects.get(name=pair_name).quote.code
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
        prepare_txn_uphold.return_value = self.generate_txn_id()
        execute_txn_uphold.return_value = {'code': 'OK'}

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, last_order_status, name)
        if last_order_status == Order.PAID and 'Uphold OK' not in name:
            txn = self.order.transactions.first()
            self.assertEqual(txn.confirmations, blockchain_confirmations, name)

    @patch('orders.models.Order._validate_status')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_release_order_only_once(self, check_tx_uphold,
                                     prepare_txn_uphold,
                                     execute_txn_uphold, _validate_status):
        _validate_status.return_value = True
        # Create order and prepare it for first release
        order, txn_dep = self._create_PAID_order()
        check_tx_uphold.return_value = True, 999
        prepare_txn_uphold.return_value = self.generate_txn_id()
        execute_txn_uphold.return_value = {'code': 'OK'}
        # Do first release
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        self.order.refresh_from_db()
        # Check things after first release
        self.assertEqual(prepare_txn_uphold.call_count, 1)
        self.assertIn(self.order.status, Order.IN_RELEASED)
        all_with_txn = self.order.transactions.filter(
            type=Transaction.WITHDRAW)
        self.assertEqual(len(all_with_txn), 1)
        # Prepare order for second release
        self.order.status = Order.PAID
        self.order.save()
        prepare_txn_uphold.return_value = self.generate_txn_id()
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        # check things after second release
        all_with_txn = self.order.transactions.filter(
            type=Transaction.WITHDRAW)
        self.assertEqual(prepare_txn_uphold.call_count, 1)
        self.order.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED)
        self.assertTrue(self.order.flagged)
        self.assertEqual(len(all_with_txn), 1)

    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_do_not_release_if_order_has_txn_without_type(self,
                                                          check_tx_uphold,
                                                          prepare_txn_uphold,
                                                          execute_txn_uphold):
        order, txn_dep = self._create_PAID_order(txn_type=None)
        check_tx_uphold.return_value = True, 999
        prepare_txn_uphold.return_value = self.generate_txn_id()
        execute_txn_uphold.return_value = {'code': 'OK'}
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        self.order.refresh_from_db()
        # Check things after first release
        self.assertEqual(prepare_txn_uphold.call_count, 0)
        self.assertIn(self.order.status, Order.IN_RELEASED)
        all_with_txn = self.order.transactions.filter(
            type=Transaction.WITHDRAW)
        self.assertEqual(len(all_with_txn), 0)
        self.assertTrue(self.order.flagged)

    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'run')
    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'do_release')
    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'validate')
    def test_do_not_release_flagged_order(self, validate, do_release,
                                          run_release):
        order, txn_dep = self._create_PAID_order()
        order.flagged = True
        order.save()
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        self.assertEqual(validate.call_count, 0)
        self.assertEqual(do_release.call_count, 0)
        self.assertEqual(run_release.call_count, 1)
        self.order.refresh_from_db()

    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_do_not_import_txn_less_bad_data(self, get_txs_uphold):
        pair_name = 'BTCLTC'
        pair = Pair.objects.get(name=pair_name)
        currency_quote_code = pair.quote.code
        amount_base = 11.11
        self._create_order(pair_name=pair_name,
                           amount_base=amount_base)
        mock_currency_code = currency_quote_code
        mock_amount = self.order.amount_quote
        card = self.order.deposit_address.reserve
        card_id = card.card_id
        bad_datas = {
            'bad amount': {'amount': mock_amount - Decimal('0.2'),
                           'currency': mock_currency_code},
            'bad currency': {'amount': mock_amount,
                             'currency': pair.base.code}
        }
        for key, value in bad_datas.items():
            get_txs_uphold.return_value = [
                self.get_uphold_tx(value['currency'], value['amount'], card_id)
            ]
            self.import_txs_task.apply()
            txns = self.order.transactions.all()
            self.assertEqual(len(txns), 0, key)

    @skip('FIXME: Uphold importer doesnt work that way on prod')
    @patch('nexchange.utils.get_address_transaction_ids_blockchain')
    @patch('accounts.tasks.monitor_wallets.check_transaction_blockchain')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_halt_deposit_tx_till_uphold_resp(self, check_tx_uphold,
                                              get_txs_uphold,
                                              prepare_txn_uphold,
                                              execute_txn_uphold,
                                              check_transaction_blockchain,
                                              get_addr_txn):
        pair_name = 'BTCLTC'
        currency_quote_code = Pair.objects.get(name=pair_name).quote.code
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
        get_addr_txn.return_value = [
            'response 200',
            [{'tx_id': self.generate_txn_id(), 'amount': mock_amount}]
        ]
        check_tx_uphold.return_value = False, 0
        blockchain_confirmations = self.order.pair.quote.min_confirmations
        check_transaction_blockchain.return_value = blockchain_confirmations
        prepare_txn_uphold.return_value = self.generate_txn_id()
        execute_txn_uphold.return_value = {'code': 'OK'}

        # Blockchain import
        self.import_txs_blockchain_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED)
        txs = self.order.transactions.all()
        self.assertEqual(len(txs), 1)
        tx = txs.last()
        self.assertIsNone(tx.tx_id_api)
        self.assertIsNotNone(tx.tx_id)

        # First update
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED)

        # Import Uphold
        self.import_txs_task.apply()
        self.order.refresh_from_db()
        txs = self.order.transactions.all()
        self.assertEqual(len(txs), 1)
        tx = txs.last()
        self.assertIsNotNone(tx.tx_id_api)
        self.assertIsNotNone(tx.tx_id)
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED)

        # Second Update
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID)
