from unittest.mock import patch, PropertyMock

from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke, \
    import_transaction_deposit_uphold_blockchain_invoke
from core.tests.base import TransactionImportBaseTestCase
from core.tests.base import UPHOLD_ROOT, EXCHANGE_ORDER_RELEASE_ROOT, \
    ETH_ROOT, SCRYPT_ROOT
from core.tests.utils import data_provider
from core.models import Transaction, Pair, Address, Currency
from orders.models import Order
from orders.task_summary import exchange_order_release_invoke,\
    exchange_order_release_periodic, buy_order_release_reference_periodic,\
    buy_order_release_by_reference_invoke
from ticker.tests.base import TickerBaseTestCase
from decimal import Decimal
from unittest import skip
from freezegun import freeze_time
from django.conf import settings
from datetime import timedelta
from payments.utils import money_format
from payments.models import Payment, PaymentMethod, PaymentPreference
import requests_mock
from http.client import RemoteDisconnected
from nexchange.api_clients.factory import ApiClientFactory
from core.common.models import Flag
from nexchange.rpc.scrypt import ScryptRpcApiClient
from django.core.exceptions import ValidationError

factory = ApiClientFactory()


class RegressionTaskTestCase(TransactionImportBaseTestCase,
                             TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['ETHLTC', 'BTCETH', 'ETHBTC', 'LTCBCH',
             'BTCLTC', 'BTCETH', 'LTCETH', 'XVGBTC']
        super(RegressionTaskTestCase, cls).setUpClass()
        cls.import_txs_task = import_transaction_deposit_crypto_invoke
        cls.import_txs_blockchain_task = \
            import_transaction_deposit_uphold_blockchain_invoke
        cls.update_confirmation_task = update_pending_transactions_invoke

    def _create_paid_order(self, **kwargs):
        txn_type = kwargs.pop('txn_type', Transaction.DEPOSIT)
        if 'pair_name' not in kwargs:
            kwargs.update({'pair_name': 'ETHLTC'})
        if 'amount_base' not in kwargs:
            kwargs.update({'amount_base': 0.5})
        order = self._create_order_api(**kwargs)
        self.move_order_status_up(order, order.status, order.PAID)
        order.refresh_from_db()
        txn_dep = order.transactions.get(type='D')
        if txn_type is not Transaction.DEPOSIT:
            txn_dep.type = txn_type
            txn_dep.save()
        return order

    def mock_blockchain_tx_checker(self, tx, confirmations, mock):
        currency = tx.currency.code
        if currency in ['BTC', 'LTC', 'ETH']:
            url = 'https://api.blockcypher.com/v1/{}/main/txs/{}'.format(
                currency.lower(), tx.tx_id)
        elif currency in ['BCH']:
            url = 'https://bitcoincash.blockexplorer.com/api/tx/{}'.format(
                tx.tx_id
            )
        response = '{{"confirmations": {}}}'.format(confirmations)
        mock.get(url, text=response)

    @skip('Uphold is not used anymore')
    @data_provider(
        lambda: (
            ('1.Bad status and confs uphold, cnfs+', 'BTCETH', True,
             (False, 0), Order.PAID),
            ('2.Bad status and confs uphold, cnfs-', 'ETHBTC', False,
             (False, 1), Order.PAID_UNCONFIRMED),
            ('3.Bad status uphold, cnfs+', 'LTCBCH', True, (False, 99),
             Order.PAID),
            ('4.Uphold OK, cnfs+', 'BTCLTC', True, (True, 99), Order.PAID),
            ('5.Uphold OK, cnfs-', 'BTCETH', False, (True, 99), Order.PAID),
            ('6.Uphold None, cnfs+', 'BTCETH', False, (None, None),
             Order.PAID_UNCONFIRMED),
        )
    )
    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_confirmation_with_blockchain(self, name, pair_name, enough_confs,
                                          uphold_checker, last_order_status,
                                          mock, check_tx_uphold,
                                          get_txs_uphold,
                                          prepare_txn_uphold,
                                          execute_txn_uphold):
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
        self.import_txs_task.apply()
        prepare_txn_uphold.return_value = self.generate_txn_id()
        execute_txn_uphold.return_value = {'code': 'OK'}

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, name)
        tx = self.order.transactions.last()
        self.mock_blockchain_tx_checker(tx, blockchain_confirmations, mock)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, last_order_status, name)
        if last_order_status == Order.PAID and 'Uphold OK' not in name:
            txn = self.order.transactions.first()
            self.assertEqual(txn.confirmations, blockchain_confirmations, name)

    @patch(ETH_ROOT + '_list_txs')
    @patch(ETH_ROOT + 'net_listening')
    @patch('orders.models.Order._validate_status')
    @patch(ETH_ROOT + 'release_coins')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_release_order_only_once(self, check_tx_uphold,
                                     release_coins_eth, _validate_status,
                                     eth_listen, eth_list_txs):
        eth_list_txs.return_value = []
        eth_listen.return_value = True
        _validate_status.return_value = True
        # Create order and prepare it for first release
        order = self._create_paid_order()
        txn_dep = order.transactions.get()
        release_coins_eth.return_value = self.generate_txn_id(), True
        # Do first release
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        order.refresh_from_db()
        # Check things after first release
        self.assertEqual(release_coins_eth.call_count, 1)
        self.assertEqual(order.status, Order.RELEASED)
        all_with_txn = order.transactions.filter(
            type=Transaction.WITHDRAW)
        self.assertEqual(len(all_with_txn), 1)
        # Prepare order for second release
        order.status = Order.PAID
        order.save()
        release_coins_eth.return_value = self.generate_txn_id(), True
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        # check things after second release
        all_with_txn = order.transactions.filter(
            type=Transaction.WITHDRAW)
        self.assertEqual(release_coins_eth.call_count, 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PRE_RELEASE)
        self.assertTrue(order.flagged)
        self.assertEqual(len(all_with_txn), 1)

    @data_provider(lambda: (
        (None,),
        (Transaction.REFUND,),
        (Transaction.WITHDRAW,),
    ))
    @patch(ETH_ROOT + 'net_listening')
    def test_do_not_release_if_order_first_tx_is_not_deposit(self, txn_type,
                                                             eth_listen):
        eth_listen.return_value = True
        order = self._create_paid_order(txn_type=txn_type)
        txn_dep = order.transactions.get()
        txn_before = order.transactions.filter(
            type=Transaction.WITHDRAW
        )
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        order.refresh_from_db()
        # Check things after first release
        self.assertEqual(order.status, Order.PRE_RELEASE)
        txn_after = order.transactions.filter(
            type=Transaction.WITHDRAW
        )
        self.assertEqual(txn_after.count() - txn_before.count(), 0, txn_type)
        self.assertTrue(order.flagged)

    @data_provider(lambda: (
        (None,),
        (Transaction.REFUND,),
        (Transaction.WITHDRAW,),
    ))
    @patch(ETH_ROOT + 'net_listening')
    def test_do_not_release_if_order_has_non_deposit_tx(self, txn_type,
                                                        eth_listen):
        eth_listen.return_value = True
        order = self._create_paid_order()
        txn_dep = order.transactions.get()
        another_tx = Transaction(type=txn_type, order=order,
                                 address_to=order.withdraw_address)
        another_tx.save()
        txn_before = order.transactions.filter(
            type=Transaction.WITHDRAW
        )
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        order.refresh_from_db()
        # Check things after first release
        self.assertEqual(order.status, Order.PRE_RELEASE)
        txn_after = order.transactions.filter(
            type=Transaction.WITHDRAW
        )
        self.assertEqual(txn_after.count() - txn_before.count(), 0, txn_type)
        self.assertTrue(order.flagged)

    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'run')
    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'do_release')
    @patch(EXCHANGE_ORDER_RELEASE_ROOT + 'validate')
    def test_do_not_release_flagged_order(self, validate, do_release,
                                          run_release):
        order = self._create_paid_order()
        order.flagged = True
        order.save()
        txn_dep = order.transactions.get()
        exchange_order_release_invoke.apply_async([txn_dep.pk])
        self.assertEqual(validate.call_count, 0)
        self.assertEqual(do_release.call_count, 0)
        self.assertEqual(run_release.call_count, 1)
        self.order.refresh_from_db()

    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_do_not_import_tx_bad_data(self, get_txs_uphold):
        pair_name = 'BTCLTC'
        pair = Pair.objects.get(name=pair_name)
        amount_base = 11.11
        self._create_order(pair_name=pair_name,
                           amount_base=amount_base)
        mock_amount = self.order.amount_quote
        card = self.order.deposit_address.reserve
        card_id = card.card_id
        bad_datas = {
            'bad currency': {'amount': mock_amount,
                             'currency': pair.base.code}
        }
        for key, value in bad_datas.items():
            get_txs_uphold.return_value = [
                self.get_uphold_tx(value['currency'], value['amount'], card_id)
            ]
            self.import_txs_task.apply()
            txs = self.order.transactions.all()
            self.assertEqual(len(txs), 0, key)

    @data_provider(
        lambda: (
            ('Less amount',
             {'pair_name': 'LTCETH', 'times': Decimal('0.89'),
              'minutes_after_expire': -4}),
            ('More amount',
             {'pair_name': 'ETHLTC', 'times': Decimal('1.23'),
              'minutes_after_expire': -4}),
            ('Expired',
             {'pair_name': 'LTCETH', 'times': Decimal('1.00'),
              'minutes_after_expire': 12}),
        ))
    @patch('orders.models.Order.get_current_slippage')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + '_get_txs')
    def test_dynamically_change_order_with_tx_import(self, name, test_data,
                                                     get_txs_scrypt,
                                                     get_txs_eth,
                                                     get_slippage):
        get_slippage.return_value = Decimal('0')
        pair_name = test_data['pair_name']
        times = test_data['times']
        self._create_order(pair_name=pair_name, amount_base=None,
                           amount_quote=11.11)
        amount_base = self.order.amount_base
        card = self.order.deposit_address.reserve
        amount_quote = self.order.amount_quote
        mock_amount = money_format(amount_quote * times, places=8)
        minutes_after_expire = test_data['minutes_after_expire']
        skip_minutes = settings.PAYMENT_WINDOW + minutes_after_expire
        now = self.order.created_on + timedelta(minutes=skip_minutes)
        with freeze_time(now):
            if minutes_after_expire >= 0:
                self.assertTrue(self.order.expired, name)

            get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                          card.address)
            get_txs_scrypt.return_value = self.get_scrypt_tx(mock_amount,
                                                             card.address)
            self.import_txs_task.apply()
            txs = self.order.transactions.all()
            self.assertEqual(len(txs), 1, name)
            tx = txs.last()
            self.assertAlmostEqual(tx.amount, mock_amount, 7, name)
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED)
            self.assertAlmostEqual(
                self.order.amount_quote, mock_amount, 7, name)
            expected_base = money_format(
                (amount_base + self.order.withdrawal_fee) *
                times - self.order.withdrawal_fee,
                places=8
            )
            self.assertAlmostEqual(
                self.order.amount_base, expected_base, 7, name)
            self.assertFalse(self.order.expired, name)
            if minutes_after_expire < 0:
                self.assertEqual(
                    self.order.payment_window, settings.PAYMENT_WINDOW, name)
            else:
                self.assertEqual(
                    self.order.payment_window,
                    settings.PAYMENT_WINDOW * 2 + minutes_after_expire,
                    name)

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

    @patch(ETH_ROOT + 'net_listening')
    @patch('core.models.Currency.available_main_reserves',
           new_callable=PropertyMock)
    def test_exchange_release_periodic(self, main_reserves, eth_listen):
        eth_listen.return_value = True
        main_reserves.return_value = Decimal('10000')
        order = self._create_paid_order()
        # Do not release not enough funds
        main_reserves.return_value = order.amount_base - Decimal('0.1')
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Release
        main_reserves.return_value = order.amount_base + Decimal('0.1')
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PRE_RELEASE)

    def test_exchange_release_periodic_do_not_flagged_tx(self):
        order = self._create_paid_order()
        tx = order.transactions.last()
        tx.flag(val='something')
        tx.refresh_from_db()
        self.assertTrue(tx.flagged)
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)

    @data_provider(lambda: (
        (False,),
        (True,)
    ))
    @patch(ETH_ROOT + 'net_listening')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_refund_order(self, pre_release, release_coins, eth_listen):
        eth_listen.return_value = True
        tx_id = self.generate_txn_id()
        release_coins.return_value = tx_id, True
        order = self._create_paid_order()
        tx_dep = order.transactions.get()
        if pre_release:
            api = factory.get_api_client(order.pair.base.wallet)
            order.pre_release(api=api)
            self.assertEqual(order.status, Order.PRE_RELEASE)
        else:
            self.assertEqual(order.status, Order.PAID)
        refund_address = Address.objects.filter(
            currency=order.pair.quote
        ).exclude(pk=order.deposit_address.pk).first()
        order.refund_address = refund_address
        order.save()
        res = order.refund()
        self.assertEqual(res['status'], 'OK', res)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.REFUNDED)
        txns = order.transactions.all()
        tx_dep.refresh_from_db()
        self.assertTrue(tx_dep.flagged)
        self.assertEqual(2, txns.count())
        tx_with = res['tx']
        self.assertEqual(tx_with.amount, tx_dep.amount)
        self.assertEqual(tx_with.amount, order.amount_quote)
        self.assertEqual(tx_with.currency, tx_dep.currency)
        self.assertEqual(tx_with.currency, order.pair.quote)
        self.assertEqual(tx_with.refunded_transaction, tx_dep)
        self.assertEqual(tx_with.order, order)
        self.assertEqual(tx_with.type, tx_with.REFUND)
        self.assertEqual(tx_with.address_to, order.refund_address)
        self.assertEqual(tx_with.tx_id, tx_id)
        order.refund()
        release_coins.assert_called_once()
        release_coins.assert_called_with(order.pair.quote,
                                         order.refund_address,
                                         order.amount_quote)

    @data_provider(lambda: (
        (Order.INITIAL,),
        (Order.CANCELED,),
        (Order.PAID_UNCONFIRMED,),
        (Order.RELEASED,),
        (Order.COMPLETED,),
    ))
    @patch('orders.models.Order._validate_status')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_refund_bad_status_order(self, status, release_coins,
                                            validate_status):
        validate_status.return_value = True
        tx_id = self.generate_txn_id()
        release_coins.return_value = tx_id, True
        order = self._create_paid_order()
        order.status = status
        refund_address = Address.objects.filter(
            currency=order.pair.quote
        ).exclude(pk=order.deposit_address.pk).first()
        order.refund_address = refund_address
        order.save()
        res = order.refund()
        self.assertEqual(res['status'], 'ERROR', res)
        order.refresh_from_db()
        self.assertEqual(order.status, status)
        release_coins.assert_not_called()

    @data_provider(lambda: (
        (Transaction.WITHDRAW,),
        (Transaction.REFUND,),
        (None,),
    ))
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_refund_order_another_tx_exists(self, tx_type,
                                                   release_coins):
        order = self._create_paid_order()
        another_tx = Transaction(address_to=order.withdraw_address,
                                 order=order, amount=order.amount_base,
                                 currency=order.pair.base, type=tx_type)
        another_tx.save()
        refund_address = Address.objects.filter(
            currency=order.pair.quote
        ).exclude(pk=order.deposit_address.pk).first()
        order.refund_address = refund_address
        order.save()
        res = order.refund()
        self.assertEqual(res['status'], 'ERROR', res)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        txns = order.transactions.all()
        self.assertEqual(2, txns.count())
        release_coins.assert_not_called()

    @data_provider(lambda: (
        ({'currency': Currency.objects.get(code='EUR')},),
        ({'amount': Decimal('123')},),
    ))
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_refund_bad_tx_data(self, tx_data, release_coins):
        order = self._create_paid_order()
        tx_dep = order.transactions.get()
        for key, value in tx_data.items():
            setattr(tx_dep, key, value)
        tx_dep.save()
        refund_address = Address.objects.filter(
            currency=order.pair.quote
        ).exclude(pk=order.deposit_address.pk).first()
        order.refund_address = refund_address
        order.save()
        res = order.refund()
        self.assertEqual(res['status'], 'ERROR', res)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        txns = order.transactions.all()
        self.assertEqual(1, txns.count())
        release_coins.assert_not_called()

    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_refund_bad_refund_address(self, release_coins):
        order = self._create_paid_order()
        refund_address = Address.objects.filter(
            currency=order.pair.base
        ).exclude(pk=order.deposit_address.pk).first()
        order.refund_address = refund_address
        order.save()
        res = order.refund()
        self.assertEqual(res['status'], 'ERROR', res)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        txns = order.transactions.all()
        self.assertEqual(1, txns.count())
        release_coins.assert_not_called()

    @patch(SCRYPT_ROOT + '_list_txs')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_release_after_wallet_connection_problems_scrypt(self,
                                                             release_coins,
                                                             scrypt_info,
                                                             list_txs):
        list_txs.return_value = []
        scrypt_info.return_value = {}
        release_coins.return_value = self.generate_txn_id(), True
        order = self._create_paid_order(pair_name='BTCLTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        scrypt_info.side_effect = Exception('Some Error')
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        release_coins.assert_not_called()
        scrypt_info.assert_called_once()
        # Release after wallet is ok
        scrypt_info.side_effect = None
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.RELEASED)
        release_coins.assert_called_once()
        self.assertEqual(scrypt_info.call_count, 2)

    @patch(SCRYPT_ROOT + '_list_txs')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_release_on_connection_timeout_scrypt(self,
                                                  release_coins,
                                                  scrypt_info, list_txs):
        list_txs.return_value = []
        release_coins.return_value = self.generate_txn_id(), True
        order = self._create_paid_order(pair_name='BTCLTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        scrypt_info.side_effect = [RemoteDisconnected('Time out!'), {}]
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.RELEASED)
        release_coins.assert_called_once()
        self.assertEqual(scrypt_info.call_count, 2)

    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_release_on_bad_info_response_scrypt(self,
                                                        release_coins,
                                                        scrypt_info):
        release_coins.return_value = self.generate_txn_id(), True
        order = self._create_paid_order(pair_name='BTCLTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        scrypt_info.return_value = 'non dict type response'
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        scrypt_info.assert_called_once()

    @patch(ETH_ROOT + '_list_txs')
    @patch(ETH_ROOT + 'net_listening')
    @patch(ETH_ROOT + 'release_coins')
    def test_release_after_wallet_connection_problems_ethash(self,
                                                             release_coins,
                                                             eth_listen,
                                                             eth_list_txs):
        eth_list_txs.return_value = []
        release_coins.return_value = self.generate_txn_id(), True
        order = self._create_paid_order(pair_name='ETHBTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        eth_listen.side_effect = Exception('Some Error')
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        release_coins.assert_not_called()
        eth_listen.assert_called_once()
        # Release after wallet is ok
        eth_listen.side_effect = None
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.RELEASED)
        release_coins.assert_called_once()
        self.assertEqual(eth_listen.call_count, 2)

    @patch(ETH_ROOT + '_list_txs')
    @patch(ETH_ROOT + 'net_listening')
    @patch(ETH_ROOT + 'release_coins')
    def test_release_after_wallet_false_listening_ethash(self,
                                                         release_coins,
                                                         eth_listen,
                                                         eth_list_txs):
        eth_list_txs.return_value = []
        release_coins.return_value = self.generate_txn_id(), True
        order = self._create_paid_order(pair_name='ETHBTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        eth_listen.return_value = False
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        release_coins.assert_not_called()
        eth_listen.assert_called_once()
        # Release after wallet is ok
        eth_listen.return_value = True
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.RELEASED)
        release_coins.assert_called_once()
        self.assertEqual(eth_listen.call_count, 2)

    @patch('orders.tasks.generic.buy_order_release.BuyOrderReleaseByReference.'
           'run')
    @patch('orders.models.Order.coverable')
    def test_buy_periodic_release_only_for_paid_orders(self, coverable,
                                                       run_release):
        coverable.return_value = True
        self._create_order(pair_name='BTCEUR')

        pref = PaymentPreference(
            provider_system_id='wawytha',
            payment_method=PaymentMethod.objects.get(
                name__icontains='Safe Charge'
            )
        )
        pref.save()
        payment = Payment(
            order=self.order,
            currency=self.order.pair.quote,
            payment_preference=pref,
            amount_cash=self.order.amount_quote,
            is_success=True,
            is_redeemed=False
        )
        payment.save()
        buy_order_release_reference_periodic.apply_async()
        run_release.assert_not_called()
        self.order.status = Order.PAID
        self.order.save()
        buy_order_release_reference_periodic.apply_async()
        run_release.assert_called_once()

    @patch('orders.models.Order.coverable')
    def test_buy_release_do_not_change_parameters_on_failure(self, coverable):
        coverable.return_value = True
        self._create_order(pair_name='BTCEUR')

        pref = PaymentPreference(
            provider_system_id='wawytha',
            payment_method=PaymentMethod.objects.get(
                name__icontains='Safe Charge'
            ),
            user=self.order.user
        )
        pref.save()
        self.order.payment_preference = pref
        withdraw_address = Address.objects.filter(
            type=Address.WITHDRAW, currency=self.order.pair.base
        ).first()
        self.order.withdraw_address = withdraw_address
        self.order.save()
        payment = Payment(
            order=self.order,
            currency=self.order.pair.quote,
            payment_preference=pref,
            amount_cash=self.order.amount_quote,
            is_success=True,
            is_redeemed=False,
            reference=self.order.unique_reference,
            user=self.order.user
        )
        payment.save()
        buy_order_release_by_reference_invoke.apply_async([payment.pk])
        payment_from_db = Payment.objects.latest('pk')
        for param in ['is_redeemed', 'is_success', 'is_complete']:
            self.assertEqual(
                getattr(payment, param),
                getattr(payment_from_db, param),
                '{}'.format(param)
            )

    @patch(ETH_ROOT + 'net_listening')
    @patch(ETH_ROOT + 'release_coins')
    def test_do_not_release_if_pre_release_save_not_working(self,
                                                            release_coins,
                                                            eth_listen):
        order = self._create_paid_order(pair_name='ETHBTC')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        # Some error raised
        with patch('orders.models.instant.Order.save'):
            exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        eth_listen.assert_called_once()
        release_coins.assert_not_called()
        # Cannot test order.flagged because save was patched
        Flag.objects.get(model_name='Order', flagged_id=order.pk)
        order.flagged = True
        order.save()
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        eth_listen.assert_called_once()
        release_coins.assert_not_called()

    @patch(SCRYPT_ROOT + '_list_txs')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_release_if_same_tx_available_scrypt(self,
                                                        release_coins,
                                                        scrypt_health,
                                                        list_txs):
        scrypt_health.return_value = {}
        order = self._create_paid_order(pair_name='BTCETH')
        list_txs.return_value = [{
            'account': '',
            'address': order.withdraw_address.address,
            'category': 'send',
            'amount': -order.amount_base,
            'txid': self.generate_txn_id(),
        }]
        scrypt_health.return_value = {}
        self._create_paid_order(pair_name='BTCETH')
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID)
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PRE_RELEASE)
        release_coins.assert_not_called()
        self.assertTrue(order.flagged)

    @data_provider(lambda: ((2,), (4,), (6,),))
    def test_input_amount_also_formatted(self, rounding):
        input_amount = Decimal('0.12345678')
        pair_name = 'BTCLTC'
        pair = Pair.objects.get(name=pair_name)
        pair.quote.rounding = rounding
        pair.quote.save()
        pair.base.rounding = rounding
        pair.base.save()
        base_order = self._create_order_api(pair_name=pair_name,
                                            amount_base=input_amount)
        self.assertEqual(
            base_order.amount_base,
            money_format(input_amount, places=rounding)
        )
        quote_order = self._create_order_api(pair_name=pair_name,
                                             amount_quote=input_amount)
        self.assertEqual(
            quote_order.amount_quote,
            money_format(input_amount, places=rounding)
        )

    @patch(SCRYPT_ROOT + '_list_txs')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def test_do_not_release_if_same_tx_available_xvg(self,
                                                     release_coins,
                                                     scrypt_health,
                                                     list_txs):
        # XVG has 6 decimal points rounding on most wallets so need
        # to make sure
        actual_rounding = 6
        legacy_rounding = 8
        xvg = Currency.objects.get(code='XVG')

        xvg.rounding = legacy_rounding
        xvg.save()
        scrypt_health.return_value = {}
        scrypt = ScryptRpcApiClient()
        amount = Decimal('100.12345678')
        order_legacy = self._create_paid_order(
            pair_name='XVGBTC', amount_base=amount
        )

        xvg.rounding = actual_rounding
        xvg.save()
        self.assertEqual(order_legacy.amount_base, amount)
        xvg.rounding = actual_rounding
        xvg.save()
        amount_on_blockchain = money_format(amount, places=actual_rounding)
        order = self._create_paid_order(pair_name='XVGBTC', amount_base=amount)
        self.assertEqual(order.amount_base, amount_on_blockchain)
        list_txs.return_value = [{
            'account': '',
            'address': order.withdraw_address.address,
            'category': 'send',
            'amount': -amount_on_blockchain,
            'txid': self.generate_txn_id(),
        }]
        scrypt_health.return_value = {}
        order.refresh_from_db()
        order.pair.base.refresh_from_db()
        with self.assertRaises(ValidationError):
            scrypt.assert_tx_unique(
                order.pair.base, order.withdraw_address, order.amount_base
            )
        order_legacy.refresh_from_db()
        order_legacy.pair.base.refresh_from_db()
        with self.assertRaises(ValidationError):
            scrypt.assert_tx_unique(
                order_legacy.pair.base, order_legacy.withdraw_address,
                order_legacy.amount_base
            )
        self.assertEqual(order.status, order.PAID)
        exchange_order_release_periodic.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PRE_RELEASE)
        release_coins.assert_not_called()
        self.assertTrue(order.flagged)
