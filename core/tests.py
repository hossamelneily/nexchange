from django.test import TestCase
from django.core.exceptions import ValidationError
from core.validators import validate_bc
from .models import Currency, Order
from django.contrib.auth.models import User


class ValidateBCTestCase(TestCase):

    def setUp(self):
        pass

    def test_validator_recognizes_bad_address(self):
        with self.assertRaises(ValidationError):
            '''valid chars but invalid address'''
            validate_bc('1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i')

        with self.assertRaises(ValidationError):
            validate_bc('invalid chars like l 0 o spaces...')

    def test_validator_recognizes_good_address(self):
        self.assertEqual(None, validate_bc(
            '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'))


class PlaceOrderTestCase(TestCase):

    def setUp(self):
        Currency(code='RUB', name='Russian Ruble').save()
        currency = Currency.objects.get(code='RUB')
        user = User.objects.create_user('+555182459988')

        self.data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': user,
            'admin_comment': 'test Order',
            'wallet': 'what goes here?',
            'unique_reference': '12345',
            'withdraw_address': None
        }

    def tearDown(self):
        data = None

    def test_can_place_order_with_good_address(self):
        withdraw_address = '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'
        self.data['withdraw_address'] = withdraw_address

        order = Order(**self.data)
        order.full_clean()  # ensure validators run
        order.save()

        fetch_order = Order.objects.get(withdraw_address=withdraw_address)
        self.assertIsInstance(fetch_order, Order)

    def test_cannot_place_order_with_bad_address(self):
        self.data['withdraw_address'] = '1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i'
        order = Order(**self.data)

        with self.assertRaises(ValidationError):
            order.full_clean()  # ensure validators run
