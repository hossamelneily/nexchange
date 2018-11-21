from .base import BaseCoreApiTestCase


class AccountApiTestCase(BaseCoreApiTestCase):

    def setUp(self, *args, **kwargs):
        super(AccountApiTestCase, self).setUp(*args, **kwargs)
        self.users_url = '/en/api/v1/users/me/'
        order, token = self._create_order_api()
        self.user = order.user
        self.profile = self.user.profile

    def test_users_me_all_data(self):
        email = 'test@super.ai'
        phone = '+37068644246'
        res = self.api_client.put(
            self.users_url,
            {'email': email, 'phone': phone}
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, email)
        self.assertEqual(self.profile.phone, phone)

    def test_users_me_all_only_mail(self):
        email = 'test@super.ai'
        res = self.api_client.put(
            self.users_url,
            {'email': email}
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, email)
        self.assertIsNone(self.profile.phone)

    def test_users_nonsense_phone_yields_none(self):
        email = 'test@super.ai'
        res = self.api_client.put(
            self.users_url,
            {'email': email, 'phone': 'sadfsdf'}
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, email)
        self.assertIsNone(self.profile.phone)
