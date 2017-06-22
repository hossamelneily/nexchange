import time
from datetime import timedelta
from unittest import skip
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.tests.base import OrderBaseTestCase
from core.tests.utils import data_provider
from core.models import Pair, Address
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from core.tests.utils import get_ok_pay_mock, create_ok_payment_mock_for_order
from payments.task_summary import run_okpay
from unittest.mock import patch
from orders.task_summary import buy_order_release_reference_periodic as \
    periodic_release, buy_order_release_by_wallet_invoke as wallet_release
from accounts.task_summary import \
    update_pending_transactions_invoke as update_txs
import random
from copy import deepcopy
from core.tests.base import UPHOLD_ROOT
from ticker.models import Ticker, Price


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
        order.status = Order.RELEASED
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
        order.status = Order.COMPLETED
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
        self.assertFalse(order.payment_status_frozen)

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


class OrderPropertiesTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderPropertiesTestCase, self).setUp()
        payment_pref = PaymentPreference.objects.get(
            identifier='okpay@nexchange.co.uk'
        )
        self.correct_pair = self.BTCUSD
        self.addr = Address(address='123456', user=self.user,
                            currency=self.BTC, type=Address.WITHDRAW)
        self.addr.save()
        data = {
            'amount_base': Decimal('1.0'),
            'pair': self.correct_pair,
            'user': self.user,
            'payment_preference': payment_pref,
            'order_type': Order.BUY,
            'withdraw_address': self.addr
        }
        self.data = deepcopy(data)
        self.data['amount_base'] = Decimal('2.0')
        self.order = Order(**data)
        self.order.save()

    def check_object_properties(self, object, properties_to_check,
                                test_case_name='Undefined',
                                check_property_len=False):
        object.refresh_from_db()
        for key, value in properties_to_check.items():
            expected = value
            real = getattr(object, key)
            if check_property_len:
                real = len(real)
            self.assertEqual(
                expected, real,
                '|Test Case Name:{name} | '
                'Assertion: {length}({obj_name}.{attr}) != {value} | '
                'Object Desc: {obj_name} == {obj_str} |'.format(
                    name=test_case_name,
                    obj_name=object.__class__.__name__.lower(),
                    attr=key,
                    value=value,
                    obj_str=object,
                    length='len' if check_property_len else ''
                )
            )

    def test_ticker_amount_calculations(self):
        ticker_amount_buy = Decimal(
            self.order.amount_base * self.order.price.ticker.ask)
        ticker_amount_sell = Decimal(
            self.order.amount_base * self.order.price.ticker.bid)
        self.assertEqual(self.order.ticker_amount, ticker_amount_buy)
        self.order.order_type = Order.SELL
        self.order.save()
        self.assertEqual(self.order.ticker_amount, ticker_amount_sell)

    def test_ticker_amount_equal_to_amount_quote(self):
        self.assertEqual(self.order.amount_quote, self.order.ticker_amount)
        # https://github.com/onitsoft/nexchange/pull/348 remove following line
        # after this PR merge
        self.order.status = Order.PAID
        self.order.amount_quote = self.order.ticker_amount / Decimal('2')
        self.order.save()
        self.assertIn('!!! amount_quote(', self.order.__str__())

    @data_provider(
        lambda: (
            ('Order 100% Paid, 1 payment(Standard situation).',
             [{'paid_part': Decimal('1.0')}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 1,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             True,
             {'status': Order.COMPLETED},
             ),
            ('Order 120% Paid, 3 payments.',
             [{'paid_part': Decimal('0.4')}, {'paid_part': Decimal('0.4')},
              {'paid_part': Decimal('0.4')}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.2')},
             {'success_payments_by_reference': 3,
              'success_payments_by_wallet': 0,
              'bad_currency_payments': 0},
             True,
             {'status': Order.COMPLETED},
             ),
            ('Order 100% Paid, wrong Payment reference. First(COMPLETED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '11111'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             True,
             {'status': Order.COMPLETED},
             ),
            ('Order 100% Paid, wrong Payment reference. SECOND(RELEASED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '22222'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             False,
             {'status': Order.RELEASED},
             ),
            ('Order 100% Paid, wrong Payment reference. THIRD(COMPLETED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '33333'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             True,
             {'status': Order.COMPLETED},
             ),
            ('Order not paid, wrong currency.',
             [{'paid_part': Decimal('1.0'),
               'pair': Pair.objects.get(name='BTCEUR')}],
             {'is_paid': False, 'is_paid_buy': False},
             {'success_payments_amount': Decimal('0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 0,
              'bad_currency_payments': 1},
             True,
             {'status': Order.INITIAL},
             ),
            ('Order 90% Paid, 2 payments.',
             [{'paid_part': Decimal('0.4')}, {'paid_part': Decimal('0.5')}],
             {'is_paid': False, 'is_paid_buy': False},
             {'success_payments_amount': Decimal('0.9')},
             {'success_payments_by_reference': 2,
              'success_payments_by_wallet': 0,
              'bad_currency_payments': 0},
             True,
             {'status': Order.INITIAL},
             ),
        )
    )
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    def test_order_is_paid(self,
                           name,
                           payments_data,
                           properties_to_check,
                           properties_times_order_amount,
                           properties_len,
                           complete_order,
                           end_properties_to_check,
                           trans_history,
                           prepare_txn,
                           execute_txn,
                           reserve_txn):
        prepare_txn.return_value = 'txid12345'
        execute_txn.return_value = True

        reserve_txn.return_value = {'status': 'completed'}
        prepare_txn.return_value = (
            '%06x' % random.randrange(16 ** 16)).upper()
        trans_history.return_value = get_ok_pay_mock(
            data='transaction_history'
        )

        order = Order(**self.data)
        order.save()
        for pay_data in payments_data:
            for key, value in pay_data.items():
                if key == 'paid_part':
                    order.amount_quote *= pay_data['paid_part']
                else:
                    setattr(order, key, value)
            trans_history.return_value = create_ok_payment_mock_for_order(
                order
            )
            order.refresh_from_db()
            run_okpay()
            payment = Payment.objects.last()
            # FIXME: remove following if statement after
            # https://app.asana.com/0/363880752769079/369754864842200 is
            # resolved
            if 'unique_reference' in pay_data:
                payment.user = order.user
                payment.save()

        for key, value in properties_times_order_amount.items():
            properties_to_check.update({key: value * order.amount_quote})
        self.check_object_properties(order, properties_to_check,
                                     test_case_name=name)
        self.check_object_properties(order, properties_len,
                                     test_case_name=name,
                                     check_property_len=True)
        expected_order_payments = max(properties_len.values())
        real_order_payments = len(Payment.objects.filter(order=order))
        self.assertEqual(expected_order_payments, real_order_payments, name)
        periodic_release.apply()
        wallet_release.apply([Payment.objects.last().pk])

        if complete_order:
            update_txs.apply()
        self.check_object_properties(order, end_properties_to_check,
                                     test_case_name=name)

    @data_provider(
        lambda: (
            ('amount_quote 1.23456789, crypto.',
             {'pair': Pair.objects.get(name='BTCLTC')},
             {'ask': 1.2346789, 'bid': 1.23456789},
             {'recommended_quote_decimal_places': 2},
             ),
            ('amount_quote 1.23456789, fiat.',
             {'pair': Pair.objects.get(name='BTCEUR')},
             {'ask': 1.2346789, 'bid': 1.23456789},
             {'recommended_quote_decimal_places': 2},
             ),
            ('amount_quote 0.123456789, crypto.',
             {'pair': Pair.objects.get(name='BTCLTC')},
             {'ask': 0.12346789, 'bid': 0.123456789},
             {'recommended_quote_decimal_places': 3},
             ),
            ('amount_quote 0.123456789, fiat.',
             {'pair': Pair.objects.get(name='BTCEUR')},
             {'ask': 0.12346789, 'bid': 0.123456789},
             {'recommended_quote_decimal_places': 2},
             ),
            ('amount_quote 0.123456789, crypto.',
             {'pair': Pair.objects.get(name='BTCLTC')},
             {'ask': 0.12346789, 'bid': 0.123456789},
             {'recommended_quote_decimal_places': 3},
             ),
            ('amount_quote 0.123456789, fiat.',
             {'pair': Pair.objects.get(name='BTCEUR')},
             {'ask': 0.12346789, 'bid': 0.123456789},
             {'recommended_quote_decimal_places': 2},
             ),
            ('amount_quote 0.0123456789, crypto.',
             {'pair': Pair.objects.get(name='BTCLTC')},
             {'ask': 0.012346789, 'bid': 0.0123456789},
             {'recommended_quote_decimal_places': 4},
             ),
        )
    )
    def test_recommended_quote_decimal_places(self, name, order_data,
                                              ticker_data,
                                              properties_to_check):
        ticker_data['pair'] = order_data['pair']
        ticker = Ticker(**ticker_data)
        ticker.save()
        price = Price(pair=ticker.pair, ticker=ticker)
        price.save()

        # amount_base == 1 for simplicity
        order_data.update({'amount_base': 1.0})
        self.data.update(order_data)
        order = Order(**self.data)
        order.save()
        self.check_object_properties(order, properties_to_check,
                                     test_case_name=name)
        order.refresh_from_db()
        expected_amount = Decimal(str(round(
            ticker.ask,
            properties_to_check['recommended_quote_decimal_places'])))
        real_amount = order.amount_quote
        self.assertEqual(expected_amount, real_amount, name)
