from core.tests.base import OrderBaseTestCase, TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from django.contrib.auth.models import User
from core.models import Address, Currency
from accounts.models import Profile
import requests_mock
from django.conf import settings


class ProfileAttributeTestCase(OrderBaseTestCase):

    def setUp(self):
        super(ProfileAttributeTestCase, self).setUp()
        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            self.user = User(username="foobar")
            self.user.save()
            self.profile = Profile(user=self.user)
            self.profile.save()

    def test_has_no_withdraw_address(self):
        self.assertFalse(self.user.profile.has_withdraw_address)

    def test_has_a_withdraw_address(self):
        address = Address(user=self.user, type=Address.WITHDRAW)
        address.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.has_withdraw_address)


class UserCreationTestCase(TransactionImportBaseTestCase, TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['LTCBTC', 'BTCLTC', 'BTCETH', 'BTCDOGE',
             'BTCXVG', 'BTCBCH', 'BTCBDG', 'BTCOMG',
             'BTCEOS', 'BTCNANO', 'BTCZEC', 'BTCUSDT',
             'BTCXMR', 'BTCKCS', 'BTCBNB', 'BTCKNC']
        super(UserCreationTestCase, cls).setUpClass()

    def test_user_count_exceeds_reserve_cards(self):
        loop_num = settings.CARDS_RESERVE_COUNT * 2
        for i in range(loop_num):
            user = User(username='User Alot{}'.format(i))
            user.save()
            profile = Profile(user=user)
            profile.save()
            self._create_an_order_for_every_crypto_currency_card(user)
            reserve_set = user.addressreserve_set.all()
            user_cards_len = len(reserve_set)
            crypto_curr = Currency.objects.filter(
                is_crypto=True, disabled=False).exclude(
                code__in=['RNS', 'GNT', 'QTM'])
            len_crypto_curr = len(crypto_curr)
            self.assertEqual(user_cards_len, len_crypto_curr)
