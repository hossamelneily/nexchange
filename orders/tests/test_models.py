import time
from datetime import timedelta, datetime
from unittest import skip
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.tests.base import OrderBaseTestCase
from core.tests.utils import data_provider, enable_all_pairs
from core.models import Pair, Address, Transaction, Currency
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from core.tests.utils import get_ok_pay_mock, create_ok_payment_mock_for_order
from payments.task_summary import run_okpay
from payments.utils import money_format
from ticker.tests.base import TickerBaseTestCase
from unittest.mock import patch
from orders.task_summary import buy_order_release_reference_periodic as \
    periodic_release, buy_order_release_by_wallet_invoke as wallet_release
from accounts.task_summary import \
    update_pending_transactions_invoke as update_txs
import random
from copy import deepcopy
from core.tests.base import UPHOLD_ROOT, SCRYPT_ROOT, ETH_ROOT
from ticker.models import Ticker, Price
from nexchange.api_clients.uphold import UpholdApiClient
from ticker.tasks.generic.crypto_fiat_ticker import CryptoFiatTicker
from ticker.tasks.generic.base import BaseTicker
from ticker.tasks.generic.base import save_ticker_and_price
import requests_mock
from freezegun import freeze_time
from rest_framework.test import APIClient
from risk_management.models import Account, DisabledCurrency, Reserve
from orders.models import FeeSource, OrderFee


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
        enable_all_pairs()

        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()

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

        order.refresh_from_db()
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

        order.refresh_from_db()
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

        order.refresh_from_db()
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
        order.refresh_from_db()
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

    def setUp(self):
        super(OrderPriceGenerationTest, self).setUp()
        enable_all_pairs()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()

    @patch('orders.models.Order.get_current_slippage')
    @patch('orders.models.Order.set_payment_preference')
    def test_auto_set_amount_cash_buy_btc_with_usd(self, set_pref,
                                                   get_slippage):
        get_slippage.return_value = Decimal('0')
        set_pref.return_value = True
        # When the client slees we buy and vice versa
        # TODO: consider different naming conventions
        amount_btc = Decimal('2.5')
        expected = \
            OrderBaseTestCase.PRICE_BUY_USD * \
            (amount_btc + self.BTCRUB.base.withdrawal_fee)
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

    @patch('orders.models.Order.get_current_slippage')
    @patch('orders.models.Order.set_payment_preference')
    def test_auto_set_amount_cash_buy_btc_with_rub(self, set_pref,
                                                   get_slippage):
        get_slippage.return_value = Decimal('0')
        set_pref.return_value = True
        amount_btc = Decimal('2.5')
        expected = \
            OrderBaseTestCase.PRICE_BUY_RUB *\
            (amount_btc + self.BTCRUB.base.withdrawal_fee)
        self.order = Order(
            order_type=Order.BUY,
            amount_base=amount_btc,
            pair=self.BTCRUB,
            user=self.user
        )
        self.order.save()

        self.assertEqual(self.order.amount_quote, expected)

    @patch('orders.models.Order.set_payment_preference')
    def test_auto_set_amount_cash_sell_btc_for_usd(self, set_pref):
        set_pref.return_value = True
        amount_btc = Decimal('2.5')
        expected = \
            OrderBaseTestCase.PRICE_SELL_USD * \
            (amount_btc + self.BTCRUB.base.withdrawal_fee)

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

    @patch('orders.models.Order.set_payment_preference')
    def test_auto_set_amount_cash_sell_btc_for_rub(self, set_pref):
        set_pref.return_value = True
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_RUB * amount_btc
        amount_btc = Decimal('2.5')
        expected = \
            OrderBaseTestCase.PRICE_SELL_RUB * \
            (amount_btc + self.BTCRUB.base.withdrawal_fee)
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
        enable_all_pairs()

        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()

        self.data = {
            'amount_base': Decimal('1.0'),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',
        }

    def get_data_provider(self, x):
        return lambda:\
            ((lambda data: Order(**data), i) for i in range(x))

    @data_provider(get_data_provider(None, 2))
    @patch('core.common.models.UniqueFieldMixin.get_random_unique_reference')
    def test_unique_token_creation(self, order_gen, counter,
                                   mock_get_random_ur):
        mock_get_random_ur.side_effect = ['AA111', 'aa111', 'aA111', 'BB2B2']
        order = order_gen(self.data)
        order.save()
        objects = Order.objects.filter(unique_reference=order.unique_reference)
        self.assertEqual(len(objects), 1)
        self.assertIsInstance(counter, int)

    @data_provider(get_data_provider(None, 2))
    @patch('core.common.models.UniqueFieldMixin.gen_unique_value')
    def test_timing_token_creation(self, order_gen, counter,
                                   mock_gen_unique_value):
        mock_gen_unique_value.side_effect = ['OCC333', 'ODD444']
        max_execution = 0.5
        start = time.time()
        order = order_gen(self.data)
        order.save()
        end = time.time()
        delta = end - start
        # plus one here is for prefix (first letter of the Class)
        self.assertEqual(settings.UNIQUE_REFERENCE_LENGTH + 1,
                         len(order.unique_reference))
        self.assertGreater(max_execution, delta)
        self.assertIsInstance(counter, int)


class OrderPropertiesTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderPropertiesTestCase, self).setUp()

        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()

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

    def check_object_properties(self, obj, properties_to_check,
                                test_case_name='Undefined',
                                check_property_len=False):
        obj.refresh_from_db()
        for key, value in properties_to_check.items():
            expected = value
            real = getattr(obj, key)
            if check_property_len:
                real = len(real)
            self.assertEqual(
                expected, real,
                '|Test Case Name:{name} | '
                'Assertion: {length}({obj_name}.{attr}) != {value} | '
                'Object Desc: {obj_name} == {obj_str} |'.format(
                    name=test_case_name,
                    obj_name=obj.__class__.__name__.lower(),
                    attr=key,
                    value=value,
                    obj_str=obj,
                    length='len' if check_property_len else ''
                )
            )

    @patch('ticker.models.Price._get_currency')
    def test_eur_usd_amounts_cache(self, get_currency):
        get_currency.return_value = Currency.objects.first()
        methods = ['amount_btc', 'amount_usd', 'amount_eur']
        for i, method in enumerate(methods):
            for _ in range(10):
                getattr(self.order, method)
            self.assertEqual(get_currency.call_count, 2 * (i + 1))

        call_count = get_currency.call_count
        now = datetime.now() + timedelta(seconds=settings.TICKER_INTERVAL + 1)
        with freeze_time(now):
            for i, method in enumerate(methods):
                getattr(self.order, method)
                self.assertEqual(
                    get_currency.call_count, 2 * (i + 1) + call_count)

    def test_ticker_amount_calculations(self):
        ticker_amount_buy = Decimal(
            self.order.amount_base * self.order.price.ticker.ask)
        ticker_amount_sell = Decimal(
            self.order.amount_base * self.order.price.ticker.bid)
        self.assertEqual(self.order.ticker_amount_quote, ticker_amount_buy)
        self.order.order_type = Order.SELL
        self.order.save()
        self.assertEqual(self.order.ticker_amount_quote, ticker_amount_sell)

    def test_ticker_amount_equal_to_amount_quote(self):
        self.assertEqual(
            self.order.amount_quote,
            self.order.ticker_amount_quote + self.order.withdrawal_fee_quote +
            self.order.minimal_payment_method_fee_quote
        )

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
             # {'status': Order.COMPLETED},
             # FIXME: CANCEL because fiat needs refactoring
             {'status': Order.CANCELED},
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
             # {'status': Order.COMPLETED},
             # FIXME: CANCEL because fiat needs refactoring
             {'status': Order.CANCELED},
             ),
            ('Order 100% Paid, wrong Payment reference. First(COMPLETED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '11111'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             True,
             # {'status': Order.COMPLETED},
             # FIXME: CANCEL because fiat needs refactoring
             {'status': Order.CANCELED},
             ),
            ('Order 100% Paid, wrong Payment reference. SECOND(RELEASED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '22222'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             False,
             # {'status': Order.RELEASED},
             # FIXME: CANCEL because fiat needs refactoring
             {'status': Order.CANCELED},
             ),
            ('Order 100% Paid, wrong Payment reference. THIRD(COMPLETED)',
             [{'paid_part': Decimal('1.0'), 'unique_reference': '33333'}],
             {'is_paid': True, 'is_paid_buy': True},
             {'success_payments_amount': Decimal('1.0')},
             {'success_payments_by_reference': 0,
              'success_payments_by_wallet': 1,
              'bad_currency_payments': 0},
             True,
             # {'status': Order.COMPLETED},
             # FIXME: CANCEL because fiat needs refactoring
             {'status': Order.CANCELED},
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
             {'status': Order.CANCELED},
             ),
        )
    )
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
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

        reserve_txn.return_value = {
            "status": "completed",
            "type": "deposit",
            "params": {"progress": 999}
        }
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
    @patch('orders.models.Order._get_minimal_payment_method_fee')
    @patch('orders.models.Order.dynamic_decimal_places')
    def test_recommended_quote_decimal_places(self, name, order_data,
                                              ticker_data,
                                              properties_to_check,
                                              dynamic_decimal_places,
                                              get_minimal_fee):
        get_minimal_fee.return_value = Decimal('0.00001')
        dynamic_decimal_places.return_value = True
        ticker_data['pair'] = order_data['pair']
        ticker = Ticker(**ticker_data)
        ticker.save()
        price = Price(pair=ticker.pair, ticker=ticker)
        price.save()

        # amount_base == 1 for simplicity
        order_data.update({
            'amount_base': Decimal(1.0) - self.data['pair'].base.withdrawal_fee
        })
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

    def test_invalid_order_than_base_amount_less_than_minimal(self):
        pair = self.data['pair']
        pair.refresh_from_db()
        self.data['amount_base'] = pair.base.minimal_amount / Decimal('2.0')

        with self.assertRaises(ValidationError):
            order = Order(**self.data)
            order.save()


class OrderStatusTestCase(TickerBaseTestCase):

    @data_provider(
        lambda: (
            ('Test INITIAL', Order.INITIAL,
             Order.IN_PAID + [Order.CANCELED, Order.PAID_UNCONFIRMED]),
            ('Test PAID_UNCONFIRMED', Order.PAID_UNCONFIRMED,
             Order.IN_PAID + [Order.CANCELED]),
            ('Test PAID', Order.PAID, Order.IN_RELEASED + [Order.CANCELED]),
            ('Test RELEASED', Order.RELEASED,
             Order.IN_COMPLETED + [Order.CANCELED]),
        )
    )
    def test_status_validator(self, name, test_status, other_statuses):
        for status in other_statuses:
            self._create_order()
            self.assertEqual(self.order.status, Order.INITIAL, name)
            self.order.status = status
            self.order.save()
            self.assertEqual(self.order.status, status, name)
            self.order.status = test_status
            with self.assertRaises(ValidationError):
                self.order.save()

    def test_order_statuses_flow(self):
        self._create_order()
        self.assertEqual(self.order.status, Order.INITIAL)
        statuses = [Order.PAID_UNCONFIRMED, Order.PAID, Order.RELEASED,
                    Order.COMPLETED]
        for status in statuses:
            self.order.status = status
            self.order.save()
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, status, status)


class OrderStateMachineTestCase(TickerBaseTestCase):

    def create_WITHDRAW_address_for_order(self, order=None):
        if order is None:
            order = self.order
        address = self.generate_txn_id()
        addr = Address(address=address, user=order.user,
                       currency=order.pair.base,
                       type=Address.WITHDRAW)
        addr.save()
        order.withdraw_address = addr
        order.save()
        return addr

    def test_txn_created_on_failed_release_coins(self):
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.save()
        self.create_WITHDRAW_address_for_order()
        txns_before = self.order.transactions.filter(type=Transaction.WITHDRAW)
        self.assertEqual(len(txns_before), 0)
        api_that_throws_error = None
        tx_data = {
            'currency': self.order.pair.base,
            'amount': self.order.amount_base,
            'order': self.order,
            'address_to': self.order.withdraw_address,
            'type': Transaction.WITHDRAW
        }
        res1 = self.order.release(tx_data, api=api_that_throws_error)
        self.assertEqual(res1['status'], 'ERROR')
        self.assertIn('assert_tx_unique', res1['message'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PRE_RELEASE)
        txns_after = self.order.transactions.filter(type=Transaction.WITHDRAW)
        self.assertEqual(len(txns_after), 1)
        res2 = self.order.release(tx_data)
        self.assertEqual(res2['status'], 'ERROR')
        self.assertIn('already has', res2['message'])

    def test_do_not_release_bad_state(self):
        '''
            State machine logic tested - only for release, because
            release sends money away
        '''
        bad_states = [Order.INITIAL, Order.PAID_UNCONFIRMED, Order.PAID,
                      Order.COMPLETED, Order.CANCELED]
        for bad_state in bad_states:
            self._create_order()
            self.order.status = bad_state
            self.order.save()
            res = self.order.release({})
            self.assertEqual(res['status'], 'ERROR')
            self.assertIn('Can\'t switch', res['message'])

    @data_provider(
        lambda: (
            ('Bad Transaction type', {'type': Transaction.DEPOSIT}, 'type'),
            ('Bad Currency', {'currency': 'Fake currency obj'}, 'Wrong'),
            ('Bad amount', {'amount': -2}, 'Wrong'),
        )
    )
    def test_release_state_errors(self, name, update_data, part_of_error_msg):
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.save()
        self.create_WITHDRAW_address_for_order()
        tx_data = {
            'currency': self.order.pair.base,
            'amount': self.order.amount_base,
            'order': self.order,
            'address_to': self.order.withdraw_address,
            'type': Transaction.WITHDRAW
        }
        tx_data.update(update_data)
        res = self.order.release(tx_data)
        self.assertEqual(res['status'], 'ERROR')
        self.assertIn(part_of_error_msg, res['message'])

    def test_do_not_replay_release(self):
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.save()
        self.create_WITHDRAW_address_for_order()
        tx_data = {
            'currency': self.order.pair.base,
            'amount': self.order.amount_base,
            'order': self.order,
            'address_to': self.order.withdraw_address,
            'type': Transaction.WITHDRAW
        }
        t = Transaction(**tx_data)
        t.save()
        res = self.order.release(tx_data)
        self.assertEqual(res['status'], 'ERROR')
        self.assertIn('already', res['message'])
        self.assertTrue(self.order.flagged)
        txns_after = self.order.transactions.filter(type=Transaction.WITHDRAW)
        self.assertEqual(len(txns_after), 1)

    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    def test_do_not_release_no_tx_id(self, release_coins):
        release_coins.return_value = None, False
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.save()
        self.create_WITHDRAW_address_for_order()
        tx_data = {
            'currency': self.order.pair.base,
            'amount': self.order.amount_base,
            'order': self.order,
            'address_to': self.order.withdraw_address,
            'type': Transaction.WITHDRAW
        }
        api = UpholdApiClient()
        res = self.order.release(tx_data, api=api)
        self.assertEqual(res['status'], 'ERROR')
        self.assertIn('Payment', res['message'])
        self.assertTrue(self.order.flagged)
        txns_after = self.order.transactions.filter(type=Transaction.WITHDRAW)
        self.assertEqual(len(txns_after), 1)


class TestSymmetricalOrder(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC']
        super(TestSymmetricalOrder, cls).setUpClass()

    def test_demo(self):
        pair = Pair.objects.get(name='BTCLTC')
        amount_base = Decimal('0.12345678')
        order1 = Order(amount_base=amount_base, pair=pair, user=self.user)
        order1.save()
        amount_quote = order1.amount_quote
        order2 = Order(amount_quote=amount_quote, pair=pair, user=self.user)
        order2.save()
        self.assertEqual(order1.amount_quote, order2.amount_quote)
        self.assertEqual(order1.amount_base, order2.amount_base)
        order3 = Order(amount_quote=amount_quote, amount_base=amount_base,
                       pair=pair, user=self.user)
        order3.save()
        self.assertEqual(order1.amount_quote, order3.amount_quote)
        self.assertEqual(order1.amount_base, order3.amount_base)

        self.assertEqual(order1.user_provided_amount, Order.PROVIDED_BASE)
        self.assertEqual(order2.user_provided_amount, Order.PROVIDED_QUOTE)
        self.assertEqual(order3.user_provided_amount, Order.PROVIDED_BOTH)


class OrderPriceTestCase(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLE_FIAT = ['USD']
        super(OrderPriceTestCase, cls).setUpClass()

    @requests_mock.mock()
    def test_pick_main_ticker(self, mock):
        pair_name = 'BTCUSD'
        pair = Pair.objects.get(name=pair_name)
        ticker_api = CryptoFiatTicker()
        mock.get(
            BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_BUY),
            text=self.localbtc_buy_resp
        )
        mock.get(
            BaseTicker.LOCALBTC_URL.format(BaseTicker.ACTION_SELL),
            text=self.localbtc_sell_resp
        )
        kraken_resp_text = '{"result": {"XXBTZUSD": {"a": ["5077.50000"],' \
                           '"b": ["5069.20000"]}}}'
        mock.get(BaseTicker.KRAKEN_TICKER,
                 text=kraken_resp_text)
        ticker, price = ticker_api.run(pair.pk, market_code='locbit')
        save_ticker_and_price(ticker, price)
        last_price = Price.objects.filter(pair=pair).last()
        self.assertFalse(last_price.market.is_main_market)
        last_main_price = Price.objects.filter(
            pair=pair, market__is_main_market=True).last()
        self._create_order(pair_name=pair_name)
        order_price = self.order.price
        self.assertEqual(order_price, last_main_price)


class CalculateOrderTestCase(TickerBaseTestCase):

    def setUp(self):
        super(CalculateOrderTestCase, self).setUp()
        self._create_order()

    def test_calculate_on_time(self):
        amount_quote = self.order.amount_quote
        amount_base = self.order.amount_base
        price = self.order.price
        times = Decimal('1.2')
        self.order.calculate_order(amount_quote * times)
        self.order.refresh_from_db()
        expected_base = money_format(
            (amount_base + self.order.withdrawal_fee) *
            times - self.order.withdrawal_fee,
            places=8
        )
        self.assertEqual(expected_base, self.order.amount_base)
        self.assertAlmostEqual(
            amount_quote * times, self.order.amount_quote, 8)
        self.assertEqual(price, self.order.price)

    @patch('orders.models.Order.expired')
    def test_calculate_expired(self, expired):
        expired.return_value = True
        price = self.order.price
        with requests_mock.mock() as m:
            self.get_tickers(m)
        latest_price = Price.objects.filter(pair=self.order.pair).last()
        ticker = latest_price.ticker
        ticker.ask = times = Decimal('1.2')
        ticker.save()
        amount_quote = self.order.amount_quote
        self.order.calculate_order(amount_quote)
        self.order.refresh_from_db()
        self.assertNotEquals(price, self.order.price)
        self.assertEqual(latest_price, self.order.price)
        self.assertEqual(amount_quote, self.order.amount_quote)
        self.assertAlmostEqual(
            self.order.amount_quote,
            (self.order.amount_base + self.order.pair.base.withdrawal_fee) * times,  # noqa
            7
        )

    def test_adjust_payment_window(self):
        default_window = self.order.payment_window
        skip_minutes = default_window + 1
        now = self.order.created_on + timedelta(minutes=skip_minutes)
        amount_quote = self.order.amount_quote
        with freeze_time(now):
            self.assertTrue(self.order.expired)
            self.order.calculate_order(amount_quote)
            self.assertFalse(self.order.expired)
            self.assertEqual(
                self.order.payment_window,
                skip_minutes + settings.PAYMENT_WINDOW)

    @patch(ETH_ROOT + '_get_tx')
    @patch(SCRYPT_ROOT + '_get_tx')
    def test_do_not_register_small_amount(self, get_tx_scrypt, get_tx_eth):
        confirmations = 999
        get_tx_scrypt.return_value = get_tx_eth.return_value = {
            'confirmations': confirmations
        }
        self._create_order(validate_amount=True)
        amount_quote = self.order.amount_quote
        amount_base = self.order.amount_base
        minimal_quote_amount = \
            self.order.pair.base.minimal_amount * self.order.price.ticker.ask
        tx_amount = minimal_quote_amount / Decimal('2.0')
        res = self.order.register_deposit(
            {'order': self.order, 'address_to': self.order.deposit_address,
             'type': Transaction.DEPOSIT, 'tx_id_api': self.generate_txn_id(),
             'amount': tx_amount, 'currency': self.order.pair.quote})
        self.assertEqual('ERROR', res['status'])
        self.assertEqual(self.order.status, Order.INITIAL)
        self.assertEqual(self.order.amount_base, amount_base)
        self.assertEqual(self.order.amount_quote, amount_quote)
        tx = self.order.transactions.last()
        self.assertEqual(tx.amount, money_format(tx_amount, places=8))
        update_txs()
        tx.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(confirmations, tx.confirmations)
        self.assertEqual(self.order.status, Order.INITIAL)


class CreateCoverableOrderTestCase(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC']
        super(CreateCoverableOrderTestCase, cls).setUpClass()

    def setUp(self):
        super(CreateCoverableOrderTestCase, self).setUp()
        self.pair = Pair.objects.get(name='BTCLTC')
        self.main_account = Account.objects.get(
            reserve__currency=self.pair.base, is_main_account=True
        )
        self.api_client = APIClient()

    def _create_order_api(self, amount_base=3):
        order_data = {
            "amount_base": amount_base,
            "pair": {
                "name": self.pair.name
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        if 'non_field_errors' in response.json():
            return
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        return order

    def test_not_create_uncoverable_order(self):
        orders_count = len(Order.objects.all())
        amount_base = Decimal(1)
        self.main_account.available = amount_base / Decimal(2)
        self.main_account.save()
        self._create_order_api(amount_base=amount_base)
        self.assertEqual(orders_count, len(Order.objects.all()))

    def test_edit_uncoverable_order(self):
        amount_base = Decimal(1)
        self.main_account.available = amount_base + Decimal('0.001')
        self.main_account.save()
        order = self._create_order_api(amount_base=amount_base)
        self.main_account.available = amount_base / Decimal(2)
        self.main_account.save()
        order.status = order.PAID_UNCONFIRMED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, order.PAID_UNCONFIRMED)

    def test_create_order_with_executable_cover(self):
        amount_base = Decimal(1)
        self.main_account.available = amount_base / Decimal(2)
        self.main_account.save()
        base = self.pair.base
        base.execute_cover = True
        base.save()
        order = self._create_order_api(amount_base=amount_base)
        self.assertFalse(order.coverable)


class DisableOrderCreationTestCase(TickerBaseTestCase):

    def __init__(self, *args, **kwargs):
        super(DisableOrderCreationTestCase, self).__init__(*args, **kwargs)
        self.api_client = APIClient()
        self.addresses = {
            'LTC': 'LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4',
            'BTC': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
            'BCH': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
        }
        self.user_reason = 'Suspended till the end of Ragnarok.'

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = \
            ['LTCBTC', 'LTCBCH', 'BCHLTC', 'BCHXVG']
        super(DisableOrderCreationTestCase, cls).setUpClass()

    def setUp(self):
        patch.stopall()
        super(DisableOrderCreationTestCase, self).setUp()
        self.patcher_validate_order_amount = patch(
            'orders.models.Order._validate_order_amount'
        )
        self.patcher_validate_order_amount.start()
        self.ltc_disabled_currency = DisabledCurrency.objects.create(
            currency=Currency.objects.get(code='LTC'),
            user_visible_reason=self.user_reason,
            disable_quote=False,
            disable_base=False
        )
        self.btc_disabled_currency = DisabledCurrency.objects.create(
            currency=Currency.objects.get(code='BTC'),
            user_visible_reason=self.user_reason,
            disable_quote=False,
            disable_base=False
        )
        self.disabled_currencies = [
            self.ltc_disabled_currency,
            self.btc_disabled_currency
        ]

    def tearDown(self):
        super(DisableOrderCreationTestCase, self).tearDown()
        self.patcher_validate_order_amount.stop()

    def _change_disablers(self, disable=False):
        for curr in self.disabled_currencies:
            curr.disable_base = disable
            curr.disable_quote = disable
            curr.save()

    def _create_order_api(self, **kwargs):
        order_data = {
            'pair': {
                'name': kwargs.pop('pair_name', 'LTCBTC')
            },
            'withdraw_address': {
                'address': kwargs.pop('address', self.addresses['LTC'])
            }
        }
        order_data.update(kwargs)
        order_api_url = '/en/api/v1/orders/'
        return self.api_client.post(order_api_url, order_data, format='json')

    def test_create_order_with_non_active_disabled_currency(self):
        self.ltc_disabled_currency.disable_quote = True
        self.ltc_disabled_currency.disable_base = False
        self.ltc_disabled_currency.save()
        self.btc_disabled_currency.disable_quote = False
        self.btc_disabled_currency.disable_base = True
        self.btc_disabled_currency.save()
        res_ok = self._create_order_api(
            pair_name='LTCBTC',
            amount_base=1,
            address=self.addresses['LTC']
        )
        self.assertEqual(res_ok.status_code, 201)

    @data_provider(lambda: (
        ('LTC', 'BCH'),
        ('BCH', 'LTC'),
    ))
    def test_do_not_create_order_with_disabled_currency(self, base, quote):
        self._change_disablers(disable=True)
        res = self._create_order_api(
            pair_name='{}{}'.format(base, quote),
            amount_quote=1,
            address=self.addresses[base]
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().pop('non_field_errors', [])
        errors_text = ''.join(errors)
        self.assertIn(self.user_reason, errors_text)

    @data_provider(lambda: (
        ('LTC', 'BCH'),
        ('BCH', 'LTC'),
        ('BCH', 'XVG'),
    ))
    def test_do_not_create_order_disabled_on_currency_model(self, base, quote):
        self._change_disablers(disable=False)
        pair = Pair.objects.get(name='{}{}'.format(base, quote))
        pair.base.disabled = True
        pair.base.save()
        res = self._create_order_api(
            pair_name=pair.name,
            amount_quote=1,
            address=self.addresses[base]
        )
        self.assertEqual(res.status_code, 400)

    def test_allow_save_after_disabling(self):
        base = self.disabled_currencies[0].currency.code
        quote = self.disabled_currencies[1].currency.code
        self._change_disablers(disable=False)
        res = self._create_order_api(
            pair_name='{}{}'.format(base, quote),
            amount_quote=1,
            address=self.addresses[base]
        )
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get(
            unique_reference=res.json()['unique_reference']
        )
        self._change_disablers(disable=True)
        self.assertIsNone(order.save())

    def test_mode_only_with_allowance(self):
        res1 = self._create_order_api(amount_quote=1)
        self.assertEqual(res1.status_code, 201)
        order = Order.objects.get(
            unique_reference=res1.json()['unique_reference']
        )
        pair = order.pair
        pair.test_mode = True
        pair.save()
        profile = order.user.profile
        self.assertFalse(profile.can_use_test_mode)
        res2 = self._create_order_api(amount_quote=1)
        self.assertEqual(res2.status_code, 400)
        profile.can_use_test_mode = True
        profile.save()
        res3 = self._create_order_api(amount_quote=1)
        self.assertEqual(res3.status_code, 201)

    def test_price_is_new(self):
        self.patcher_validate_order_create_price.stop()
        res1 = self._create_order_api(amount_quote=1)
        order = Order.objects.get(
            unique_reference=res1.json()['unique_reference']
        )
        self.assertEqual(res1.status_code, 201)
        now = datetime.now() + settings.TICKER_EXPIRATION_INTERVAL
        with freeze_time(now):
            res2 = self._create_order_api(amount_quote=1)
            self.assertEqual(res2.status_code, 400)
            self.assertIsNone(order.save())

    def test_do_not_sell_lower_than_min_reserves(self):
        self.patcher_validate_order_reserve.stop()
        pair = Pair.objects.get(name='LTCBTC')
        reserve = Reserve.objects.get(currency=pair.base)
        mininum_level = reserve.minimum_level
        accounts = reserve.account_set.all()
        min_per_account_available = mininum_level / Decimal(accounts.count())
        for acc in accounts:
            acc.available = min_per_account_available * Decimal(0.9)
            acc.save()
        res = self._create_order_api(
            pair_name=pair.name,
            amount_quote=1,
            address=self.addresses[pair.base.code]
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(pair.base.is_base_of_enabled_pair)
        self.assertTrue(pair.base.is_base_of_enabled_pair_for_test)

    def test_do_not_buy_higher_than_max_reserves(self):
        self.patcher_validate_order_reserve.stop()
        pair = Pair.objects.get(name='LTCBTC')
        reserve = Reserve.objects.get(currency=pair.quote)
        maximum_level = reserve.maximum_level
        accounts = reserve.account_set.filter(disabled=False)
        max_per_account_available = maximum_level / Decimal(accounts.count())
        for acc in accounts:
            acc.available = max_per_account_available * Decimal(1.1)
            acc.save()
        res = self._create_order_api(
            pair_name=pair.name,
            amount_quote=1,
            address=self.addresses[pair.base.code]
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(pair.quote.is_quote_of_enabled_pair)
        self.assertTrue(pair.quote.is_quote_of_enabled_pair_for_test)


class OrderFeesTestCase(OrderBaseTestCase):

    def __init__(self, *args, **kwargs):
        super(OrderFeesTestCase, self).__init__(*args, *kwargs)
        self.api_client = APIClient()

    def setUp(self, *args, **kwargs):
        super(OrderFeesTestCase, self).setUp(*args, **kwargs)
        self.markup_fee_source = FeeSource.objects.get(name='Markup')
        self.payment_method_fee_source = \
            FeeSource.objects.get(name='Payment Method')
        self.withdrawal_fee_source = FeeSource.objects.get(name='Withdrawal')

    def _create_order_api(self, **order_data):
        order_data.update({
            'pair': {
                'name': 'BTCEUR'
            },
            'withdraw_address': {
                'address': '15TpiR1wMZKQAGz2Z5djUae2PPkRLpDv4H'
            }
        })
        order_api_url = '/en/api/v1/orders/'
        res = self.api_client.post(order_api_url, order_data, format='json')
        return Order.objects.get(
            unique_reference=res.json()['unique_reference']
        )

    def test_log_fees(self):
        order_big = self._create_order_api(amount_quote='500')
        order_quote = self._create_order_api(amount_quote='100')
        order_base = self._create_order_api(
            amount_base=str(order_quote.amount_base)
        )
        order_big.calculate_order(order_quote.amount_quote)
        order_big.save()
        tot_base_fee = tot_quote_fee = Decimal('0')
        for fee_source in [OrderFee.WITHDRAWAL, OrderFee.PAYMENT_METHOD]:
            oquote_fee = order_quote.orderfee_set.get(
                fee_source__name=fee_source
            )
            obase_fee = order_base.orderfee_set.get(
                fee_source__name=fee_source
            )
            obig_fee = order_big.orderfee_set.get(
                fee_source__name=fee_source
            )
            self.assertEqual(oquote_fee.amount_base,
                             obase_fee.amount_base)
            self.assertEqual(oquote_fee.amount_base,
                             obig_fee.amount_base)
            tot_base_fee += oquote_fee.amount_base
            self.assertEqual(oquote_fee.amount_quote,
                             obase_fee.amount_quote)
            self.assertEqual(oquote_fee.amount_quote,
                             obig_fee.amount_quote)
            tot_quote_fee += oquote_fee.amount_quote
        oquote_fee = order_quote.orderfee_set.get(
            fee_source__name=OrderFee.MARKUP
        )
        obase_fee = order_base.orderfee_set.get(
            fee_source__name=OrderFee.MARKUP
        )
        obig_fee = order_big.orderfee_set.get(
            fee_source__name=OrderFee.MARKUP
        )
        self.assertEqual(oquote_fee.amount_base,
                         obase_fee.amount_base)
        self.assertEqual(oquote_fee.amount_base,
                         obig_fee.amount_base)
        self.assertEqual(oquote_fee.amount_quote,
                         obase_fee.amount_quote)
        self.assertEqual(oquote_fee.amount_quote,
                         obig_fee.amount_quote)
        current_fee = order_quote.pair.fee_ask_current
        markup_multip = \
            Decimal('1') / (Decimal('1') + current_fee) * current_fee
        expected_base = \
            (order_quote.amount_base - tot_base_fee) * markup_multip
        expected_quote = \
            (order_quote.amount_quote - tot_quote_fee) * markup_multip
        self.assertAlmostEqual(expected_base, oquote_fee.amount_base, 8)
        self.assertAlmostEqual(expected_quote, oquote_fee.amount_quote, 8)


class SuggestTrustpilotTestCase(OrderBaseTestCase):

    def __init__(self, *args, **kwargs):
        super(SuggestTrustpilotTestCase, self).__init__(*args, **kwargs)
        self.api_client = APIClient()

    def _test_trustpilot_link_on_notify_msg(self, order, is_on=True):
        self.assertEqual(order.status, order.RELEASED)
        self.assertTrue(order.user.email)
        with patch('orders.models.instant.send_email') as send_patch:
            order.notify()
        self.assertEqual(send_patch.call_count, 1)
        _assertion = 'assertIn' if is_on else 'assertNotIn'
        getattr(self, _assertion)('trustpilot.com', send_patch.call_args[0][2])
        getattr(self, _assertion)('Trustpilot', send_patch.call_args[0][2])

    def test_suggested_to_fast_orders(self):
        order = self._create_order_api()
        user = order.user
        user.email = 'hey@hey.hey'
        user.save()
        self.move_order_status_up(order, order.status, order.RELEASED)
        order.refresh_from_db()
        self.assertTrue(order.suggest_trustpilot)
        self._test_trustpilot_link_on_notify_msg(order)
        # Suggest if second order is fast too
        order2 = self._create_order_api()
        self.move_order_status_up(order2, order.status, order.RELEASED)
        order2.refresh_from_db()
        self.assertEqual(order.user, order2.user)
        self.assertTrue(order2.suggest_trustpilot)
        self._test_trustpilot_link_on_notify_msg(order2)

    def test_do_not_suggest_if_first_one_slow(self):
        order = self._create_order_api()
        user = order.user
        user.email = 'hey@hey.hey'
        user.save()
        now = datetime.now() + timedelta(
            seconds=settings.FAST_CREATE_TO_RELEASE_TIME_SECONDS + 1
        )
        with freeze_time(now):
            self.move_order_status_up(order, order.status, order.RELEASED)
        order.refresh_from_db()
        self.assertFalse(order.suggest_trustpilot)
        self._test_trustpilot_link_on_notify_msg(order, is_on=False)
        # Do not suggest second order because first was slow
        order2 = self._create_order_api()
        self.move_order_status_up(order2, order.status, order.RELEASED)
        order2.refresh_from_db()
        self.assertEqual(order.user, order2.user)
        self.assertTrue(order2.is_released_fast)
        self.assertFalse(order2.suggest_trustpilot)
        self._test_trustpilot_link_on_notify_msg(order2, is_on=False)
