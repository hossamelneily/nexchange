from django.test import Client, TestCase
from rest_framework.test import APIClient
from support.models import Support
from unittest.mock import patch


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


class SupportApiTest(TestCase):

    def setUp(self):
        self.post_data = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }

    def test_form_saved(self):
        client = APIClient()

        support_count = Support.objects.count()
        response = client.post(
            '/en/api/v1/support/',
            data=self.post_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Support.objects.count(), support_count + 1)

    @patch('support.task_summary.send_support_email.run')
    def test_send_email_task_created(self, checker_run):
        client = APIClient()
        response = client.post(
            '/en/api/v1/support/',
            data=self.post_data)
        self.assertEqual(checker_run.call_count, 1)
