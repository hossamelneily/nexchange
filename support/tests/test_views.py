from django.test import TestCase, Client
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


class SupportFormTest(TestCase):
    """
    Tests the response when the form is correctly filled
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

        self.post_data = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }

    def test_form_filled(self):
        response = self.client.post('/support/',
                                    self.post_data,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
