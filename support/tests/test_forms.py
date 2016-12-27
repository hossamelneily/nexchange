from django.test import TestCase
from orders.models import Order
from support.forms import SupportForm
from core.tests.base import UserBaseTestCase, OrderBaseTestCase
from decimal import Decimal
from django.test.client import RequestFactory


class SupportTestForm(TestCase):
    """Test is user is not authenticated"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_valid_form(self):
        data = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        request = self.factory.get('/support/')
        request.user = None
        form = SupportForm(data=data, request=request)
        self.assertTrue(form.is_valid())

    def test_invalid_form(self):
        data = {
            'name': 'TestSupport',
            'email': '',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        request = self.factory.get('/support/')
        request.user = None
        form = SupportForm(data=data, request=request)
        self.assertFalse(form.is_valid())


class SupportTestModelUser(UserBaseTestCase, OrderBaseTestCase):
    """Test is user is authenticated"""

    def setUp(self):
        super(SupportTestModelUser, self).setUp()
        self.factory = RequestFactory()

        currency = self.RUB
        self.data = {
            'amount_cash': Decimal(30674.85),
            'amount_btc': Decimal(1.00),
            'currency': currency,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345'
        }

        self.order = Order(**self.data)
        self.order.save()

    def test_valid_form(self):
        data_form = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        request = self.factory.get('/support/')
        request.user = self.user
        form = SupportForm(data=data_form, request=request)
        self.assertTrue(form.is_valid())

    def test_invalid_form(self):
        data_form = {
            'name': 'TestSupport',
            'email': '',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        request = self.factory.get('/support/')
        request.user = self.user
        form = SupportForm(data=data_form, request=request)
        self.assertFalse(form.is_valid())
