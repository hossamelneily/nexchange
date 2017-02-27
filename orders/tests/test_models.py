import time
from datetime import timedelta
from unittest import skip
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.tests.base import OrderBaseTestCase
from core.tests.utils import data_provider
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference


class OrderBasicFieldsTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderBasicFieldsTestCase, self).setUp()
        self.data = {
            'amount_base': Decimal('1.0'),
            'pair': self.BTCUSD,
            'user': self.user,
            'admin_comment': 'tests Order',
        }

    def test_limit_order_type_choices(self):
        to_big_integer = max([i[0] for i in Order.TYPES]) + 1
        to_small_integer = min([i[0] for i in Order.TYPES]) - 1
        for order_type in [to_big_integer, to_small_integer]:
            self.data['order_type'] = order_type
            with self.assertRaises(ValidationError):
                order = Order(**self.data)
                order.save()

    def test_limit_status_choices(self):
        to_big_integer = max([i[0] for i in Order.STATUS_TYPES]) + 1
        to_small_integer = min([i[0] for i in Order.STATUS_TYPES]) - 1
        for status in [to_big_integer, to_small_integer]:
            self.data['status'] = status
            with self.assertRaises(ValidationError):
                order = Order(**self.data)
                order.save()

    def test_help_texts(self):
        for field in Order._meta.fields:
            if field.name in ['order_type', 'status']:
                self.assertNotEqual(
                    field.help_text, '',
                    'Field {}  helpt_text should not be empty'.format(
                        field.name
                    )
                )


class OrderValidatePaymentTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderValidatePaymentTestCase, self).setUp()
        self.data = {
            'amount_base': Decimal('1.0'),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',

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
        order.save()
        order.status = Order.PAID
        order.save()

        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        # deadline is in the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # but already paid
        self.assertTrue(order.status == Order.PAID)

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
        self.assertTrue(order.payment_status_frozen)

        # even though it's not paid
        self.assertFalse(order.status > Order.PAID)

    def test_frozen_if_released(self):
        # As user input is irrelevant once order is paid
        order = Order(**self.data)
        order.save()
        order.status = Order.PAID
        order.save()

        order = Order.objects.last()
        # it's paid
        self.assertTrue(order.status == Order.RELEASED)

        # therefore it's frozen
        self.assertTrue(order.payment_status_frozen)

        # even though deadline is in the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_frozen_if_completed(self):
        # As user input is irrelevant once order is paid
        order = Order(**self.data)
        order.save()
        order.status = Order.PAID
        order.save()

        order = Order.objects.last()
        # it's paid
        self.assertTrue(order.status == Order.COMPLETED)

        # therefore it's frozen
        self.assertTrue(order.payment_status_frozen)

        # even though deadline is in the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_not_frozen_if_paid(self):
        # As user input is irrelevant once order is paid
        order = Order(**self.data)
        order.save()
        order.status = Order.PAID
        order.save()

        order = Order.objects.last()
        # it's paid
        self.assertTrue(order.status == Order.PAID)

        # therefore it's frozen
        self.assertFalse(order.payment_status_frozen)

        # even though deadline is in the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_not_frozen_if_paid_internally(self):
        order = Order(**self.data)
        order.save()
        order.status = Order.PAID
        order.save()
        payment_method = PaymentMethod(
            name='Internal Test',
            is_internal=True
        )
        payment_method.save()

        pref = PaymentPreference(
            payment_method=payment_method,
            user=order.user,
            identifier='InternalTestIdentifier'
        )
        pref.save()

        payment = Payment(
            payment_preference=pref,
            amount_cash=order.amount_quote,
            order=order,
            user=order.user,
            currency=order.pair.quote
        )
        payment.save()
        order = Order.objects.last()
        # it's paid
        self.assertTrue(order.status == Order.PAID)

        # therefore it's frozen
        self.assertTrue(order.payment_status_frozen)

        # even though deadline is in the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_is_not_frozen_if_is_not_paid_neither_expired(self):
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        order.save()

        order = Order.objects.last()

        # it's not paid
        self.assertFalse(order.status >= Order.PAID)

        # also it's not expired
        self.assertFalse(order.expired)

        # so it's not frozen
        self.assertFalse(order.payment_status_frozen)


class OrderPriceGenerationTest(OrderBaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderPriceGenerationTest, cls).setUpClass()

    def test_auto_set_amount_cash_buy_btc_with_usd(self):
        # When the client slees we buy and vice versa
        # TODO: consider different naming conventions
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_USD * amount_btc
        self.order = Order(
            order_type=Order.BUY,
            amount_base=amount_btc,
            pair=self.BTCUSD,
            user=self.user
        )
        self.order.save()

        self.assertEqual(self.order.amount_quote, expected)

    @skip("causes failures, needs to be migrated")
    def test_auto_set_amount_cash_buy_btc_with_eur(self):
        # When the client slees we buy and vice versa
        # TODO: consider different naming conventions
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_RUB / \
            OrderBaseTestCase.RATE_EUR * amount_btc
        self.order = Order(order_type=Order.BUY, amount_btc=amount_btc,
                           currency=self.EUR, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_buy_btc_with_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_RUB * amount_btc
        self.order = Order(
            order_type=Order.BUY,
            amount_base=amount_btc,
            pair=self.BTCRUB,
            user=self.user
        )
        self.order.save()

        self.assertEqual(self.order.amount_quote, expected)

    def test_auto_set_amount_cash_sell_btc_for_usd(self):
        amount_btc = 2.5

        expected = OrderBaseTestCase.PRICE_SELL_USD * amount_btc

        self.order = Order(
            order_type=Order.SELL,
            amount_base=amount_btc,
            pair=self.BTCUSD,
            user=self.user
        )
        self.order.save()

        self.assertEqual(self.order.amount_quote, expected)

    @skip("causes failures, needs to be migrated")
    def test_auto_set_amount_cash_sell_btc_for_eur(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_RUB / \
            OrderBaseTestCase.RATE_EUR * amount_btc
        self.order = Order(
            order_type=Order.SELL,
            amount_from=amount_btc,
            currency_from=self.BTC,
            currency_to=self.EUR,
            user=self.user
        )
        self.order.save()

        self.assertEqual(self.order.amount_to, expected)

    def test_auto_set_amount_cash_sell_btc_for_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_RUB * amount_btc
        self.order = Order(
            order_type=Order.SELL,
            amount_base=amount_btc,
            pair=self.BTCRUB,
            user=self.user
        )
        self.order.save()
        self.assertEqual(self.order.amount_quote, expected)


class OrderUniqueReferenceTestsCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderUniqueReferenceTestsCase, self).setUp()
        self.data = {
            'amount_base': Decimal('1.0'),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',
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

    @data_provider(get_data_provider(None, 3000))
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


class OrderCurrencyTypesTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderCurrencyTypesTestCase, self).setUp()
        self.data = {
            'amount_base': Decimal('1.0'),
            'user': self.user
        }
        self.assertTrue(self.BTC.is_crypto)
        self.CRYPTO = self.BTC
        self.assertFalse(self.USD.is_crypto)
        self.FIAT = self.USD

    @skip('legacy')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_buy_from_fiat_to_crypto(self, convert):
        convert.return_value = True
        self.data.update({
            'order_type': Order.BUY,
            'currency_from': self.FIAT,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        order.save()

    @skip('legacy')
    @patch('orders.models.Order._not_same_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_buy_to_fiat(self, convert, not_same):
        convert.return_value = True
        not_same.return_value = True
        self.data.update({
            'order_type': Order.BUY,
            'currency_from': self.FIAT,
            'currency_to': self.FIAT
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order._not_same_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_buy_from_crypto(self, convert, not_same):
        convert.return_value = True
        not_same.return_value = True
        self.assertTrue(self.BTC.is_crypto)
        self.data.update({
            'order_type': Order.BUY,
            'currency_from': self.CRYPTO,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_sell_from_crypto_to_fiat(self, convert):
        convert.return_value = True
        self.data.update({
            'order_type': Order.SELL,
            'currency_from': self.CRYPTO,
            'currency_to': self.FIAT
        })
        order = Order(**self.data)
        order.save()

    @skip('legacy')
    @patch('orders.models.Order._not_same_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_sell_to_crypto(self, convert, not_same):
        convert.return_value = True
        not_same.return_value = True
        self.data.update({
            'order_type': Order.SELL,
            'currency_from': self.CRYPTO,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order._not_same_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_sell_from_fiat(self, convert, not_same):
        convert.return_value = True
        not_same.return_value = True
        self.data.update({
            'order_type': Order.SELL,
            'currency_from': self.FIAT,
            'currency_to': self.FIAT
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order._not_same_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_exchange_from_crypto_to_crypto(self, convert, not_same):
        convert.return_value = True
        not_same.return_value = True
        self.data.update({
            'order_type': Order.EXCHANGE,
            'currency_from': self.CRYPTO,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        order.save()

    @skip('legacy')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_exchange_from_fiat(self, convert):
        convert.return_value = True
        self.data.update({
            'order_type': Order.EXCHANGE,
            'currency_from': self.FIAT,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_exchange_to_fiat(self, convert):
        convert.return_value = True
        self.data.update({
            'order_type': Order.EXCHANGE,
            'currency_from': self.CRYPTO,
            'currency_to': self.FIAT
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()

    @skip('legacy')
    @patch('orders.models.Order._order_types_currencies_validator')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_fail_same_currency_convertion(self, convert, order_types):
        convert.return_value = True
        order_types.return_value = True
        self.data.update({
            'order_type': Order.EXCHANGE,
            'currency_from': self.CRYPTO,
            'currency_to': self.CRYPTO
        })
        order = Order(**self.data)
        with self.assertRaises(ValidationError):
            order.save()
