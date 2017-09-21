from core.tests.base import TransactionImportBaseTestCase
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
import random
from django.conf import settings
from unittest import skip
from nexchange.api_clients.uphold import UpholdApiClient
from accounts.task_summary import update_pending_transactions_invoke


class TransactionImportTaskTestCase(TransactionImportBaseTestCase,
                                    TickerBaseTestCase):

    def setUp(self):
        super(TransactionImportTaskTestCase, self).setUp()
        self.run_method = import_transaction_deposit_crypto_invoke.apply
        with requests_mock.mock() as mock:
            self.get_tickers(mock)
            self._mock_cards_reserve(mock)
            self._create_an_order_for_every_crypto_currency_card(self.user)

    def test_create_transactions_with_task(self):
        self.base_test_create_transactions_with_task(self.run_method)

    def test_create_transactions_with_None_currency_address(self):
        self.address, created = Address.objects.get_or_create(
            name='test address',
            address=self.wallet_address,
            user=self.user,
            type=Address.DEPOSIT
        )

        with requests_mock.mock() as mock:
            self.get_tickers(mock)
        self.base_test_create_transactions_with_task(self.run_method)


class AddressReserveMonitorTestCase(TransactionImportBaseTestCase,
                                    TickerBaseTestCase):

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
        self.client = UpholdApiClient()
        self.monitor = ReserveMonitor(self.client, wallet='api1')
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
        ('Send funds, currency ok, balance more than 0', 'ETH', 'ETH', '1.1',
         1, {'retry': False, 'success': True}),
        ('Do not release, bad currency', 'BTC', 'ETH', '2.0', 0,
         {'retry': False, 'success': False}),
        ('Do not release, balance == 0', 'LTC', 'LTC', '0.0', 0,
         {'retry': True, 'success': False}),
    ),)
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @requests_mock.mock()
    def test_send_funds_to_main_card(self, name, curr_code, main_curr_code,
                                     amount, release_call_count,
                                     resend_funds_res, release_coins, mock):
        release_coins.return_value = (
            '%06x' % random.randrange(16 ** 16)).upper(), True
        card = self.user.addressreserve_set.get(currency__code=curr_code)
        card_url = self.url_base + card.card_id
        main_card_id = self.monitor.client.coin_card_mapper(curr_code)
        main_address_name = self.monitor.client.address_name_mapper(curr_code)
        main_card_url = self.url_base + main_card_id
        mock.get(
            card_url,
            text='{{"currency":"{}","balance": "{}"}}'.format(curr_code,
                                                              amount)
        )
        mock.get(
            main_card_url,
            text='{{"currency":"{}","address":{{"{}":"dfasf"}}}}'.format(
                main_curr_code, main_address_name
            )
        )
        res1 = self.monitor.client.resend_funds_to_main_card(card.card_id,
                                                             curr_code)
        res2 = self.monitor.client.check_card_balance(card.pk)
        self.assertEqual(release_coins.call_count, release_call_count * 2,
                         name)
        for key, value in resend_funds_res.items():
            self.assertEqual(res1[key], value, name)
            self.assertEqual(res2[key], value, name)


    @skip('Cards must be checked card by card')
    @patch('accounts.tasks.generic.addressreserve_monitor.base.'
           'ReserveMonitor.check_cards')
    def test_check_cards_task(self, check_cards):
        # check_cards_uphold_invoke.apply()
        self.assertEqual(1, check_cards.call_count)

    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_card_balance')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_retry_balance_check_x_times(self, check_tx, check_card):
        check_card.return_value = {'retry': True}
        check_tx.return_value = True, 999
        self._create_order()
        self.order.register_deposit(
            {'order': self.order, 'address_to': self.order.deposit_address,
             'type': Transaction.DEPOSIT, 'tx_id_api': self.generate_txn_id()})
        update_pending_transactions_invoke.apply()
        tx = self.order.transactions.last()
        check_transaction_card_balance_invoke.apply([tx.pk])
        self.assertEqual(check_card.call_count,
                         settings.RETRY_CARD_CHECK_MAX_RETRIES + 1)

    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_card_balance')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_retry_balance_check_success(self, check_tx, check_card):
        check_card.return_value = {'retry': True}
        check_tx.return_value = True, 999
        self._create_order()
        self.order.register_deposit(
            {'order': self.order, 'address_to': self.order.deposit_address,
             'type': Transaction.DEPOSIT, 'tx_id_api': self.generate_txn_id()})
        update_pending_transactions_invoke.apply()
        tx = self.order.transactions.last()
        check_card.return_value = {'retry': False}
        check_transaction_card_balance_invoke.apply([tx.pk])
        self.assertEqual(check_card.call_count, 1)
