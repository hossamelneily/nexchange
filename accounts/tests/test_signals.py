from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from accounts.tasks.generate_wallets import renew_cards_reserve
from django.contrib.auth.models import User
import requests_mock
from core.models import AddressReserve as Cards
from core.models import Currency
from accounts.models import Profile
from django.conf import settings
from unittest.mock import patch
from accounts.task_summary import check_cards_uphold_invoke
from unittest import skip


class RenewReserveTestCase(TransactionImportBaseTestCase, TickerBaseTestCase):

    def setUp(self):
        super(RenewReserveTestCase, self).setUp()
        Cards.objects.all().delete()
        self.len_crypto_curencies = len(Currency.objects.filter(
            disabled=False, is_crypto=True)
        )
        with requests_mock.mock() as mock:
            self.get_tickers(mock)

    @requests_mock.mock()
    def test_expected_reserve_default(self, mock):
        self._mock_cards_reserve(mock)
        renew_cards_reserve()
        len_reserve_cards = len(Cards.objects.filter(
            disabled=False, user=None))
        len_expected = self.len_crypto_curencies * settings.CARDS_RESERVE_COUNT
        self.assertEqual(len_reserve_cards, len_expected)

    @requests_mock.mock()
    def test_expected_reserve_user_emergency(self, mock):
        self._mock_cards_reserve(mock)
        user = User(username='Flame McFirehead')
        user.save()
        profile = Profile(user=user)
        profile.save()
        self._create_an_order_for_every_crypto_currency_card(user)
        len_user_cards = len(Cards.objects.filter(
            disabled=False, user__isnull=False))
        len_reserve_cards = len(Cards.objects.filter(
            disabled=False, user__isnull=True))
        len_expected = \
            self.len_crypto_curencies * settings.EMERGENCY_CARDS_RESERVE_COUNT
        self.assertEqual(len_user_cards, len_expected)
        self.assertEqual(len_reserve_cards, 0)

    @skip('check_cards must be refactored')
    @requests_mock.mock()
    def test_2_users_1_card(self, mock):
        with patch(
                'nexchange.api_clients.uphold.'
                'AddressReserve.objects.filter') as filter:
            with patch(
                    'nexchange.api_clients.base.BaseApiClient.'
                    'renew_cards_reserve') as allocate_reserver:
                filter.return_value = []
                allocate_reserver.return_value = True
                user1 = User(username='Parallel1')
                user1.save()
                profile1 = Profile(user=user1)
                profile1.save()
        # user1 created, but has no cards
        self.assertEqual(len(user1.addressreserve_set.all()), 0)
        self._mock_cards_reserve(mock)
        # user2 steals user1 cards
        renew_cards_reserve(expected_reserve=1)
        user2 = User(username='Parallel2')
        user2.save()
        profile2 = Profile(user=user2)
        profile2.save()
        self.assertEqual(len(user2.addressreserve_set.all()),
                         self.len_crypto_curencies)
        self._mock_cards_reserve(mock)
        check_cards_uphold_invoke.apply()
        self.assertEqual(len(user1.addressreserve_set.all()),
                         self.len_crypto_curencies)
