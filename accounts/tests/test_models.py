from core.tests.base import OrderBaseTestCase
from django.contrib.auth.models import User
from core.models import Address
from accounts.models import Profile
import requests_mock


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
