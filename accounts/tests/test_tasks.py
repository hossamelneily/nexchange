from core.tests.base import TransactionImportBaseTestCase, ETH_ROOT, OMNI_ROOT
from core.models import Address, Currency, AddressReserve, Transaction
from accounts.task_summary import import_transaction_deposit_crypto_invoke,\
    check_transaction_card_balance_invoke
from ticker.tests.base import TickerBaseTestCase
import requests_mock
from django.contrib.auth.models import User
from accounts.models import Profile
from accounts.tasks.generic.addressreserve_monitor.base import ReserveMonitor
from core.tests.utils import data_provider
from unittest.mock import patch
from django.conf import settings
from unittest import skip
from nexchange.rpc.ethash import EthashRpcApiClient
from nexchange.rpc.omni import OmniRpcApiClient
from accounts.task_summary import update_pending_transactions_invoke
import os
from decimal import Decimal

RPC7_KEY1 = '0xmain'
RPC10_KEY1 = 'USDT_address'


class TransactionImportTaskTestCase(TransactionImportBaseTestCase,
                                    TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(TransactionImportTaskTestCase, cls).setUpClass()
        cls.run_method = import_transaction_deposit_crypto_invoke.apply

    def setUp(self):
        super(TransactionImportTaskTestCase, self).setUp()

    @skip('Uphold is not used anymore')
    def test_create_transactions_with_task(self):
        self.base_test_create_transactions_with_task(self.run_method)

    @skip('Uphold is not used anymore')
    def test_create_transactions_with_None_currency_address(self):
        self.address, created = Address.objects.get_or_create(
            name='test address',
            address=self.wallet_address,
            user=self.user,
            type=Address.DEPOSIT
        )

        self.base_test_create_transactions_with_task(self.run_method)


class AddressReserveMonitorTestCase(TransactionImportBaseTestCase,
                                    TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['LTCBTC', 'BTCLTC', 'BTCETH', 'BTCDOGE',
             'BTCXVG', 'BTCBCH', 'BTCBDG', 'BTCOMG',
             'BTCEOS', 'BTCNANO', 'BTCZEC', 'BTCUSDT',
             'BTCXMR', 'BTCKCS', 'BTCBNB', 'BTCKNC',
             'BTCBIX', 'BTCHT', 'BTCCOSS', 'BTCBNT',
             'BTCCOB']
        super(AddressReserveMonitorTestCase, cls).setUpClass()

    def setUp(self):
        super(AddressReserveMonitorTestCase, self).setUp()
        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            self.user, created = \
                User.objects.get_or_create(username='Address von Monitor')
            self.user.save()
            self.profile = Profile(user=self.user)
            self.profile.save()
        self.currency = Currency.objects.get(code='ETH')
        self.client_ethash = EthashRpcApiClient()
        self.monitor_eth = ReserveMonitor(self.client_ethash, wallet='rpc7')
        self.client_omni = OmniRpcApiClient()
        self.monitor_omni = ReserveMonitor(self.client_omni, wallet='rpc10')
        self.url_base = 'https://api.uphold.com/v0/me/cards/'
        with requests_mock.mock() as mock:
            self.get_tickers(mock)
        self._create_an_order_for_every_crypto_currency_card(self.user)
        self.old_wallets_ids = self._get_wallets_ids()

    def _get_wallets_ids(self):
        wallets_ids = {
            card.currency.code: card.card_id for card in
            self.user.addressreserve_set.filter(disabled=False,
                                                currency__wallet='api1')
        }
        return wallets_ids

    @skip('Uphold is not used anymore')
    @requests_mock.mock()
    def test_replace_wallet(self, mock):
        currency_code = 'ETH'
        self._mock_cards_reserve(mock)
        self.monitor.client.replace_wallet(self.user, currency_code)
        other_wallets = self.user.addressreserve_set.filter(
            disabled=False, currency__wallet='api1').exclude(
            currency__code=currency_code)
        for wallet in other_wallets:
            self.assertEqual(
                wallet.card_id, self.old_wallets_ids[wallet.currency.code])
        replaced_wallet = self.user.addressreserve_set.get(
            disabled=False, currency__code=currency_code)
        self.assertNotEqual(
            replaced_wallet.card_id, self.old_wallets_ids[currency_code])

    @skip('check_cards needs refactoring')
    @data_provider(lambda: (
        ('All wallets ok', 'OK', 'assertEqual',),
        ('Wallets not found', 'Not Found', 'assertNotEqual',),
    ),)
    @requests_mock.mock()
    def test_check_cards(self, name, msg, card_ids_assert, mock):
        self._mock_cards_reserve(mock)
        for card_id in self.old_wallets_ids.values():
            mock.get('https://api.uphold.com/v0/me/cards/' + card_id,
                     text='{{"message": "{}"}}'.format(msg))
        self.assertFalse(self.profile.cards_validity_approved, name)
        self.monitor.check_cards()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.cards_validity_approved, name)
        wallets = self._get_wallets_ids()
        for key, value in wallets.items():
            getattr(self, card_ids_assert)(
                self.old_wallets_ids[key], value, name
            )
        self.profile.cards_validity_approved = False
        self.profile.save()

    @skip('check_cards needs to be refactore')
    @requests_mock.mock()
    def test_check_cards_when_user_has_no_cards(self, mock):
        cards = self.user.addressreserve_set.all()
        addresses = self.user.address_set.all()
        for_disable = [cards, addresses]
        for objs in for_disable:
            for obj in objs:
                obj.user = None
                obj.disabled = True
                obj.save()
        self.profile.cards_validity_approved = True
        self.profile.save()
        self._mock_cards_reserve(mock)
        self.monitor.check_cards()
        wallets = self._get_wallets_ids()
        for key, value in wallets.items():
            self.assertNotEqual(
                self.old_wallets_ids[key], value
            )

    @skip('check_cards needs refactoring')
    @requests_mock.mock()
    def test_check_cards_multiple_times(self, mock):
        all_cards_len = len(AddressReserve.objects.filter(disabled=True))
        crypto_currencies_len = len(Currency.objects.filter(is_crypto=True))
        checks_count = settings.CARDS_RESERVE_COUNT * 3
        for i in range(checks_count):
            self._mock_cards_reserve(mock)
            wallets = self._get_wallets_ids()
            for card_id in wallets.values():
                mock.get(self.url_base + card_id,
                         text='{"message": "Not Found"}')
            self.monitor.check_cards()
            all_cards_len_after = len(
                AddressReserve.objects.filter(disabled=True))
            user_cards_len = len(self.user.addressreserve_set.all())
            self.assertEqual(
                all_cards_len_after,
                all_cards_len + crypto_currencies_len * (i + 1)
            )
            self.assertEqual(user_cards_len, crypto_currencies_len)
            self.profile.cards_validity_approved = False
            self.profile.save()

    @data_provider(lambda: (
        ('Send funds, balance more than 0', 'ETH', '1.1', '0.1',
         1, {'retry': False, 'success': True}, False),
        ('Send funds, balance more than 0', 'EOS', '1.1', '0.1',
         1, {'retry': False, 'success': True}, False),
        ('Send funds, balance more than 0', 'BDG', '1.1', '0',
         0, {'retry': True, 'success': False}, False),
        ('Do not release, balance == 0', 'ETH', '0.0', '0', 0,
         {'retry': True, 'success': False}, False),
        ('Release error', 'ETH', '1.1', '0.1',
         1, {'retry': True, 'success': False}, True),
        ('Send funds, balance more than 0', 'USDT', '1.1', '0.1',
         1, {'retry': False, 'success': True}, False),
        ('Do not release, balance == 0', 'USDT', '0.0', '0', 0,
         {'retry': True, 'success': False}, False),
    ),)
    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': RPC7_KEY1})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch.dict(os.environ, {'RPC10_PUBLIC_KEY_C1': RPC10_KEY1})
    @patch(ETH_ROOT + 'get_accounts')
    @patch('web3.eth.Eth.call')
    @patch('web3.eth.Eth.getBalance')
    @patch(ETH_ROOT + 'release_coins')
    @patch(OMNI_ROOT + 'release_coins')
    @patch(OMNI_ROOT + 'get_accounts')
    @patch(OMNI_ROOT + 'get_balance')
    @patch(OMNI_ROOT + 'get_unspent_address_balance')
    def test_send_funds_to_main_card(self, name, curr_code,
                                     amount, amount_main, release_call_count,
                                     resend_funds_res, raise_value_error,
                                     get_unspent_address_balance_omni,
                                     get_balance_omni,
                                     get_accs_omni, release_coins_omni,
                                     release_coins_eth, get_balance_eth,
                                     get_balance_erc20, get_accs_eth):
        get_accs_eth.return_value = [RPC7_KEY1.upper()]
        get_accs_omni.return_value = [RPC10_KEY1]
        if raise_value_error:
            release_coins_eth.side_effect = release_coins_omni.side_effect = \
                ValueError('Locked wallet')
        else:
            release_coins_eth.return_value = \
                release_coins_omni.return_value = \
                self.generate_txn_id(), True
        card = self.user.addressreserve_set.get(currency__code=curr_code)
        currency = Currency.objects.get(code=curr_code)
        value_eth = int(Decimal(amount) * (10 ** currency.decimals))
        value_omni = Decimal(amount)

        if currency.wallet == 'rpc7':
            get_balance_erc20.return_value = hex(value_eth)
            if currency.is_token:
                main_value = int(Decimal(amount_main) * (10 ** 18))
                get_balance_eth.return_value = main_value
            else:
                get_balance_eth.return_value = value_eth

            res1 = self.monitor_eth.client.resend_funds_to_main_card(
                card.card_id,
                curr_code
            )
            res2 = self.monitor_eth.client.check_card_balance(card.pk)
            self.assertEqual(release_coins_eth.call_count,
                             release_call_count * 2,
                             name)
            amount_to_send = Decimal(
                amount) - self.client_ethash.get_total_gas_price(
                currency.is_token
            )
            if currency.is_token:
                amount_to_send = Decimal(amount)
            if release_call_count:
                release_coins_eth.assert_called_with(
                    currency, '0xmain', amount_to_send,
                    address_from=card.address
                )
        elif currency.wallet == 'rpc10':
            get_balance_omni.return_value = {'balance': value_omni,
                                             'pending': 0,
                                             'available': value_omni}

            get_unspent_address_balance_omni.return_value = \
                Decimal('0.00030000')
            res1 = self.monitor_omni.client.resend_funds_to_main_card(
                card.card_id,
                curr_code
            )
            res2 = self.monitor_omni.client.check_card_balance(card.pk)
            self.assertEqual(release_coins_omni.call_count,
                             release_call_count * 2,
                             name)
            amount_to_send = \
                get_balance_omni.return_value.get('available', Decimal('0'))
            if release_call_count:
                release_coins_omni.assert_called_with(
                    currency, RPC10_KEY1, amount_to_send,
                    address_from=card.address
                )

        for key, val in resend_funds_res.items():
            self.assertEqual(res1[key], val, name)
            self.assertEqual(res2[key], val, name)

    @skip('Cards must be checked card by card')
    @patch('accounts.tasks.generic.addressreserve_monitor.base.'
           'ReserveMonitor.check_cards')
    def test_check_cards_task(self, check_cards):
        # check_cards_uphold_invoke.apply()
        self.assertEqual(1, check_cards.call_count)

    @patch(ETH_ROOT + 'check_card_balance')
    @patch(ETH_ROOT + 'check_tx')
    def test_retry_balance_check_x_times(self, check_tx, check_card):
        check_card.return_value = {'retry': True}
        check_tx.return_value = True, 999
        self._create_order(pair_name='BTCETH')
        self.order.register_deposit(
            {'order': self.order, 'address_to': self.order.deposit_address,
             'type': Transaction.DEPOSIT, 'tx_id': self.generate_txn_id(),
             'amount': self.order.amount_quote, 'currency':
                 self.order.pair.quote}
        )
        update_pending_transactions_invoke.apply()
        tx = self.order.transactions.last()
        check_transaction_card_balance_invoke.apply([tx.pk])
        self.assertEqual(check_card.call_count,
                         settings.RETRY_CARD_CHECK_MAX_RETRIES + 1)

    @patch(ETH_ROOT + 'check_card_balance')
    @patch(ETH_ROOT + 'check_tx')
    def test_retry_balance_check_success(self, check_tx, check_card):
        check_card.return_value = {'retry': True}
        check_tx.return_value = True, 999
        self._create_order(pair_name='BTCETH')
        self.order.register_deposit(
            {'order': self.order, 'address_to': self.order.deposit_address,
             'type': Transaction.DEPOSIT, 'tx_id': self.generate_txn_id(),
             'amount': self.order.amount_quote,
             'currency': self.order.pair.quote}
        )
        update_pending_transactions_invoke.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, self.order.PAID)
        tx = self.order.transactions.last()
        check_card.return_value = {'retry': False}
        check_transaction_card_balance_invoke.apply([tx.pk])
        self.assertEqual(check_card.call_count, 1)
