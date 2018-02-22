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
from unittest import skip
import os
from core.tests.base import RPC8_WALLET, RPC8_PUBLIC_KEY_C1, RPC8_PORT,\
    RPC8_HOST, RPC8_USER, RPC8_PASSWORD


class RenewReserveTestCase(TransactionImportBaseTestCase, TickerBaseTestCase):

    def setUp(self):
        super(RenewReserveTestCase, self).setUp()
        Cards.objects.all().delete()
        self.len_crypto_curencies = len(Currency.objects.filter(
            disabled=False, is_crypto=True).exclude(code__in=[
                'RNS', 'GNT', 'QTM'])
        )
        with requests_mock.mock() as mock:
            self.get_tickers(mock)

    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
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
            disabled=False, user__isnull=False).exclude(currency__code='RNS'))
        len_reserve_cards = len(Cards.objects.filter(
            disabled=False, user__isnull=True).exclude(currency__code='RNS'))
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
        self.assertEqual(len(user1.addressreserve_set.all()),
                         self.len_crypto_curencies)
