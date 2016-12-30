from django.test import TestCase

from core.tests.base import UserBaseTestCase


class SupportTestView(TestCase):
    """Test is user is not authenticated"""

    def test_support_view(self):
        response = self.client.get('/support/', follow=True)
        self.assertEqual(response.status_code, 200)


class SupportTestUserView(UserBaseTestCase):
    """Test is user is authenticated"""

    def test_support_user_view(self):
        response = self.client.get('/support/', follow=True)
        self.assertEqual(response.status_code, 200)
