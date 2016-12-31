from django.test import Client, TestCase

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

    def test_redirect_at_success(self):
        response = self.client.post('/support/',
                                    self.post_data,
                                    follow=True)
        last_url, last_status_code = \
            response.redirect_chain[-1]
        self.assertEquals(last_url, '/en/support/')
        self.assertEquals(last_status_code, 302)

    def test_redirect_at_failure(self):
        del self.post_data['email']
        response = self.client.post('/support/',
                                    {},
                                    follow=True)
        last_url, last_status_code = \
            response.redirect_chain[-1]
        self.assertEquals(last_url, '/en/support/')
        self.assertEquals(last_status_code, 302)
        self.assertEquals(response.status_code, 200)
