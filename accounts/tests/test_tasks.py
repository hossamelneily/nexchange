from core.tests.base import TransactionImportBaseTestCase
from core.models import Address, Currency, AddressReserve
from accounts.task_summary import import_transaction_deposit_crypto_invoke,\
    check_cards_balances_uphold_invoke, check_cards_uphold_invoke
from core.tests.base import OrderBaseTestCase
import requests_mock
from django.contrib.auth.models import User
from accounts.models import Profile
from accounts.tasks.generic.addressreserve_monitor.uphold import \
    UpholdReserveMonitor
from core.tests.utils import data_provider
from unittest.mock import patch
import random
from django.conf import settings


class TransactionImportTaskTestCase(TransactionImportBaseTestCase):

    def setUp(self):
        super(TransactionImportTaskTestCase, self).setUp()
        self.run_method = import_transaction_deposit_crypto_invoke.apply

    def test_create_transactions_with_task(self):
        self.base_test_create_transactions_with_task(self.run_method)

    def test_create_transactions_with_None_currency_address(self):
        self.address, created = Address.objects.get_or_create(
            name='test address',
            address=self.wallet_address,
            user=self.user,
            type=Address.DEPOSIT
        )
        self.base_test_create_transactions_with_task(self.run_method)


class AddressReserveMonitorTestCase(OrderBaseTestCase):

    def setUp(self):
        super(AddressReserveMonitorTestCase, self).setUp()
        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            self.user, created = \
                User.objects.get_or_create(username='Address von Monitor')
            self.user.save()
            self.profile = Profile(user=self.user)
            self.profile.save()
        cards = AddressReserve.objects.filter().exclude(user=self.user)
        for card in cards:
            card.need_balance_check = False
            card.save()
        self.currency = Currency.objects.get(code='ETH')
        self.old_wallets_ids = self._get_wallets_ids()
        self.monitor = UpholdReserveMonitor()
        self.url_base = 'https://api.uphold.com/v0/me/cards/'

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
        ('Send funds, currency ok, balance more than 0', 'ETH', 'ETH', '1.1', 1),  # noqa
        ('Do not release, bad currency', 'BTC', 'ETH', '2.0', 0),
        ('Do not release, balance == 0', 'LTC', 'LTC', '0.0', 0),
    ),)
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @requests_mock.mock()
    def test_send_funds_to_main_card(self, name, curr_code, main_curr_code,
                                     amount, release_call_count, release_coins,
                                     mock):
        release_coins.return_value = (
            '%06x' % random.randrange(16 ** 16)).upper()
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
        self.monitor.client.resend_funds_to_main_card(card.card_id, curr_code)
        self.assertEqual(release_coins.call_count, release_call_count, name)

    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @requests_mock.mock()
    def test_check_card_balances(self, release_coins, mock):
        release_coins.return_value = (
            '%06x' % random.randrange(16 ** 16)).upper()
        cards = self.user.addressreserve_set.filter(currency__wallet='api1')
        for card in cards:
            card.refresh_from_db()
            self.assertTrue(card.need_balance_check)
            curr_code = card.currency.code
            card_url = self.url_base + card.card_id
            main_card_id = self.monitor.client.coin_card_mapper(curr_code)
            main_address_name = self.monitor.client.address_name_mapper(
                curr_code)
            main_card_url = self.url_base + main_card_id
            mock.get(
                card_url,
                text='{{"currency":"{}","balance": "1.1"}}'.format(curr_code)
            )
            mock.get(
                main_card_url,
                text='{{"currency":"{}","address":{{"{}":"dfasf"}}}}'.format(
                    curr_code, main_address_name
                )
            )
        for _ in range(len(cards)):
            self.monitor.client.check_cards_balances()
        for card in cards:
            card.refresh_from_db()
            self.assertFalse(card.need_balance_check)

    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_cards_balances')
    def test_check_balances_task(self, check_balances):
        check_cards_balances_uphold_invoke.apply()
        self.assertEqual(1, check_balances.call_count)

    @patch('accounts.tasks.generic.addressreserve_monitor.uphold.'
           'UpholdReserveMonitor.check_cards')
    def test_check_cards_task(self, check_cards):
        check_cards_uphold_invoke.apply()
        self.assertEqual(1, check_cards.call_count)
