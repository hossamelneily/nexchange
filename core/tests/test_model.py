from django.test import TestCase
from django.core.exceptions import ValidationError
from core.validators import validate_bc
from django.utils import timezone
from core.models import Order
from datetime import timedelta
import time
from django.conf import settings


from .utils import UserBaseTestCase, data_provider
from .test_order import OrderBaseTestCase


class OrderValidatePaymentTestCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(OrderValidatePaymentTestCase, self).setUp()
        currency = self.RUB
        self.data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': self.user,
            'admin_comment': 'test Order',

        }

    def test_payment_deadline_calculation(self):
        created_on = timezone.now()
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        expected = created_on + timedelta(minutes=payment_window)
        order.save()
        # ignore ms
        self.assertTrue(abs(expected - order.payment_deadline) <
                        timedelta(seconds=1))

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

        # deadline is in the past
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

        # deadline is in the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # so it's frozen
        self.assertTrue(order.frozen)

        # even though it's not paid
        self.assertFalse(order.is_paid)

    def test_is_frozen_if_paid(self):
        order = Order(**self.data)
        order.is_paid = True
        order.save()

        order = Order.objects.last()

        # it's paid
        self.assertTrue(order.is_paid)

        # therefore it's frozen
        self.assertTrue(order.frozen)

        # even though deadline is in the future
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


class OrderPriceGenerationTest(OrderBaseTestCase, UserBaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderPriceGenerationTest, cls).setUpClass()

    def test_auto_set_amount_cash_buy_btc_with_usd(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_USD * amount_btc
        self.order = Order(order_type=Order.BUY, amount_btc=amount_btc,
                           currency=self.USD, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_buy_btc_with_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_RUB * amount_btc
        self.order = Order(order_type=Order.BUY, amount_btc=amount_btc,
                           currency=self.RUB, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_sell_btc_for_usd(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_USD * amount_btc
        self.order = Order(order_type=Order.SELL, amount_btc=amount_btc,
                           currency=self.USD, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_sell_btc_for_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_RUB * amount_btc
        self.order = Order(order_type=Order.SELL, amount_btc=amount_btc,
                           currency=self.RUB, user=self.user)
        self.order.save()
        self.assertEqual(self.order.amount_cash, expected)


class OrderUniqueReferenceTestsCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(OrderUniqueReferenceTestsCase, self).setUp()
        self.data = {
            'amount_cash': 36000,
            'amount_btc': 1,
            'currency': self.RUB,
            'user': self.user,
            'admin_comment': 'test Order',
        }

    def get_data_provider(self, x):
        return lambda:\
            ((lambda data: Order(**data), i) for i in range(x))

    @data_provider(get_data_provider(None, 1000))
    def test_unique_token_creation(self, order_gen, counter):
        order = order_gen(self.data)
        order.save()
        objects = Order.objects.filter(unique_reference=order.unique_reference)
        self.assertEqual(len(objects), 1)
        self.assertIsInstance(counter, int)

    @data_provider(get_data_provider(None, 10000))
    def test_timing_token_creation(self, order_gen, counter):
        max_execution = 0.5
        start = time.time()
        order = order_gen(self.data)
        order.save()
        end = time.time()
        delta = end - start
        self.assertEqual(settings.UNIQUE_REFERENCE_LENGTH,
                         len(order.unique_reference))
        self.assertGreater(max_execution, delta)
        self.assertIsInstance(counter, int)


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
