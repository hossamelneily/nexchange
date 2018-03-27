from decimal import Decimal

from django.test import TestCase
from django.test.client import RequestFactory

from core.tests.base import OrderBaseTestCase, UserBaseTestCase
from orders.models import Order
from support.forms import SupportForm
from unittest import skip
from core.models import Currency


class SupportTestForm(TestCase):
    """Test is user is not authenticated"""

    def setUp(self):
        self.factory = RequestFactory()

    @skip('This form is not currently used (API is used instead!)')
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

    def test_invalid_form_name(self):
        data = {
            'name': '',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        request = self.factory.get('/support/')
        request.user = None
        form = SupportForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_invalid_form_email(self):
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

    def test_invalid_form_message(self):
        data = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': ''
        }
        request = self.factory.get('/support/')
        request.user = None
        form = SupportForm(data=data, request=request)
        self.assertFalse(form.is_valid())


class SupportTestModelUserOrder(OrderBaseTestCase):
    """Test is user is authenticated and order is created"""

    def setUp(self):
        super(SupportTestModelUserOrder, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()
        self.factory = RequestFactory()

        pair = self.BTCRUB
        self.data = {
            'amount_quote': Decimal(30674.85),
            'amount_base': Decimal(1.00),
            'pair': pair,
            'user': self.user,
            'admin_comment': 'tests Order'
        }

        self.order = Order(**self.data)
        self.order.save()

    @skip('This form is not currently used (API is used instead!)')
    def test_valid_form(self):
        data_form = {
            'name': 'TestSupport',
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test',
            'unique_reference': 'mock',
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


class SupportTestModelUser(UserBaseTestCase):
    """Test is user is authenticated and order is not created"""

    def setUp(self):
        super(SupportTestModelUser, self).setUp()
        self.factory = RequestFactory()

    @skip('This form is not currently used (API is used instead!)')
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
