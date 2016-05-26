from django.test import TestCase
from .models import Currency, Order
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone


class ValidateOrderPaymentTestCase(TestCase):

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
            'unique_reference': '12345'
        }
        pass

    def test_payment_deadline_calculation(self):
        created_on = timezone.now()
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        order.save()

        expected = created_on + timedelta(minutes=payment_window)

        order = Order.objects.last()
        order.created_on = created_on

        self.assertEqual(expected, order.payment_deadline)

    def test_is_expired_after_payment_deadline(self):
        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        self.assertTrue(order.expired)

    def test_is_not_expired_if_paid(self):

        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.is_paid = True
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        # deadline i int the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # but already paid
        self.assertTrue(order.is_paid)

        # so it's not expired
        self.assertFalse(order.expired)

    def test_is_frozen_if_expired(self):
        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        # deadline is int the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # so it's frozen
        self.assertTrue(order.frozen)

        # even tough it's not paid
        self.assertFalse(order.is_paid)

    def test_is_frozen_if_paid(self):
        order = Order(**self.data)
        order.is_paid = True
        order.save()

        order = Order.objects.last()

        # it's not paid
        self.assertTrue(order.is_paid)

        # therefor it's frozen
        self.assertTrue(order.frozen)

        # even tough deadline is int the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_is_not_frozen_if_is_not_paid_neither_expired(self):
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        order.save()

        order = Order.objects.last()

        # it's not paid
        self.assertFalse(order.is_paid)

        # also it's not expired
        self.assertFalse(order.expired)

        # so it's not frozen
        self.assertFalse(order.frozen)
