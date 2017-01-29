from core.tests.base import OrderBaseTestCase
from payments.models import Payment, PaymentPreference
from orders.task_summary import buy_order_release
from django.contrib.auth.models import User
from orders.models import Order
from core.models import Address
from decimal import Decimal
from unittest.mock import patch
from copy import deepcopy
from django.db import transaction


class ReleaseOderTestCase(OrderBaseTestCase):

    def setUp(self):
        super(ReleaseOderTestCase, self).setUp()
        currency = self.RUB
        self.addr = Address(address='12345', user=self.user)
        self.addr.save()
        self.our_pref = PaymentPreference.objects.first()
        self.data = {
            'amount_cash': Decimal(30674.85),
            'amount_btc': Decimal(1.00),
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '123456',
            'payment_preference': self.our_pref,
            'currency': currency,
            'withdraw_address': self.addr
        }
        self.order = Order(**self.data)
        self.order.save()

        self.pref = PaymentPreference(
            payment_method=self.order.payment_preference.payment_method,
            user=self.order.user,
            identifier='123456',
        )

        self.pref.save()
        self.pref.currency.add(self.order.currency)
        self.pref.save()

        self.good_payment_data = {
            'user': self.order.user,
            'currency': self.order.currency,
            'payment_preference': self.pref,
            'amount_cash': self.order.amount_cash,
            'is_success': True
        }
        self.good_payment = None

        self.exact_payment_data = deepcopy(self.good_payment_data)
        self.exact_payment_data['reference'] = self.order.unique_reference
        self.exact_payment = None

        self.bad_payment_amount_data = deepcopy(self.good_payment_data)
        self.bad_payment_amount_data['amount_cash'] /= 2
        self.bad_payment_amount = None

        self.bad_user = User.objects.create(username='Hacker')
        self.bad_user.save()
        self.bad_payment_sender_data = deepcopy(self.good_payment_data)
        self.bad_payment_sender_data['user'] = self.bad_user
        self.bad_payment_sender = None

        self.bad_payment_currency_data = deepcopy(self.good_payment_data)
        self.bad_payment_currency_data['currency'] = self.EUR
        self.bad_payment_currency = None

        self.bad_payment_failure_data = deepcopy(self.good_payment_data)
        self.bad_payment_failure_data['is_success'] = False
        self.bad_payment_failure = None

    def tearDown(self):
        with transaction.atomic(using='default'):
            self.order.delete()
            self.pref.delete()
            if self.good_payment:
                self.good_payment.delete()

            if self.bad_payment_amount:
                self.bad_payment_amount.delete()

            if self.bad_payment_sender:
                self.bad_payment_sender.delete()
                self.bad_user.delete()

            if self.bad_payment_currency:
                self.bad_payment_currency.delete()

            if self.bad_payment_failure:
                self.bad_payment_failure.delete()

            if self.exact_payment:
                self.exact_payment.delete()

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_success_reference(
            self, send_email, send_sms, release_payment):
        self.exact_payment = Payment(**self.exact_payment_data)
        self.exact_payment.save()

        release_payment.return_value = 'A555B'
        buy_order_release.apply()
        self.exact_payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_released)
        self.assertTrue(self.exact_payment.is_redeemed)
        self.assertTrue(self.exact_payment.is_complete)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_success_cross_check(
            self, send_email, send_sms, release_payment):
        release_payment.return_value = 'A555B'
        self.good_payment = Payment(**self.good_payment_data)
        self.good_payment.save()
        buy_order_release.apply()
        # reload from db
        self.order.refresh_from_db()
        self.good_payment.refresh_from_db()
        # test
        self.assertTrue(self.order.is_released)
        self.assertTrue(self.good_payment.is_redeemed)
        self.assertTrue(self.good_payment.is_complete)
        self.assertEqual(1, release_payment.call_count)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_only_once(self, send_email, send_sms, release_payment):
        release_payment.return_value = 'A555B'
        self.good_payment = Payment(**self.good_payment_data)
        self.good_payment.save()
        buy_order_release.apply()
        # reload from db
        self.order.refresh_from_db()
        self.good_payment.refresh_from_db()
        # test
        self.assertTrue(self.order.is_released)
        self.assertTrue(self.good_payment.is_redeemed)
        self.assertTrue(self.good_payment.is_complete)
        self.assertEqual(1, release_payment.call_count)

        buy_order_release.apply()
        # test only once
        self.assertTrue(self.order.is_released)
        self.assertTrue(self.good_payment.is_redeemed)
        self.assertTrue(self.good_payment.is_complete)
        self.assertEqual(1, release_payment.call_count)

    # TODO: migrate to data provider
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_fail_no_payment(
            self, send_email, send_sms, release_payment):
        release_payment.return_value = 'A555B'
        buy_order_release.apply()
        # reload from db
        self.order = Order.objects.get(pk=self.order.pk)

        # test
        self.assertFalse(self.order.is_released)
        self.assertEqual(0, release_payment.call_count)

    # TODO: migrate to data provider
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_fail_payment_not_success(
            self, send_email, send_sms, release_payment):
        self.bad_payment_failure = \
            Payment(**self.bad_payment_failure_data)
        self.bad_payment_failure.save()

        # apply task
        buy_order_release.apply()

        # reload from db
        self.order = Order.objects.get(pk=self.order.pk)

        # test
        self.assertFalse(self.order.is_released)
        self.assertEqual(0, release_payment.call_count)

        self.assertFalse(self.order.is_released)
        self.assertFalse(self.bad_payment_failure.is_redeemed)
        self.assertFalse(self.bad_payment_failure.is_complete)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_fail_payment_wrong_user(
            self, send_email, send_sms, release_payment):
        self.bad_payment_sender = \
            Payment(**self.bad_payment_sender_data)
        self.bad_payment_sender.save()

        # apply task
        buy_order_release.apply()

        # reload from db
        self.order = Order.objects.get(pk=self.order.pk)

        # test
        self.assertFalse(self.order.is_released)
        self.assertEqual(0, release_payment.call_count)

        self.assertFalse(self.order.is_released)
        self.assertFalse(self.bad_payment_sender.is_redeemed)
        self.assertFalse(self.bad_payment_sender.is_complete)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_fail_payment_wrong_amount(
            self, send_email, send_sms, release_payment):
        self.bad_payment_amount = \
            Payment(**self.bad_payment_amount_data)
        self.bad_payment_amount.save()

        # apply task
        buy_order_release.apply()

        # reload from db
        self.order.refresh_from_db()
        self.bad_payment_amount.refresh_from_db()

        # test
        self.assertFalse(self.order.is_released)
        self.assertEqual(0, release_payment.call_count)

        self.assertFalse(self.order.is_released)
        self.assertFalse(self.bad_payment_amount.is_redeemed)
        self.assertFalse(self.bad_payment_amount.is_complete)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_release_fail_payment_wrong_currency(
            self, send_email, send_sms, release_payment):
        self.bad_payment_currency = \
            Payment(**self.bad_payment_currency_data)
        self.bad_payment_currency.save()

        # apply task
        buy_order_release.apply()

        # reload from db
        self.order.refresh_from_db()
        self.bad_payment_currency.refresh_from_db()
        # test
        self.assertFalse(self.order.is_released)
        self.assertEqual(0, release_payment.call_count)

        self.assertFalse(self.order.is_released)
        self.assertFalse(self.bad_payment_currency.is_redeemed)
        self.assertFalse(self.bad_payment_currency.is_complete)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_bad_payments_dont_block_good_payments(self, send_email,
                                                   send_sms, release_payment):
        def make_asserts(payment):
            self.assertFalse(payment.is_redeemed)
            self.assertFalse(payment.is_complete)

        self.bad_payment_currency = \
            Payment(**self.bad_payment_currency_data)
        self.bad_payment_currency.save()

        self.bad_payment_amount = \
            Payment(**self.bad_payment_amount_data)
        self.bad_payment_amount.save()

        self.bad_payment_sender = \
            Payment(**self.bad_payment_sender_data)
        self.bad_payment_sender.save()

        self.bad_payment_failure = \
            Payment(**self.bad_payment_failure_data)
        self.bad_payment_failure.save()

        # reload and assert
        elems = [
            self.bad_payment_failure,
            self.bad_payment_sender,
            self.bad_payment_amount,
            self.bad_payment_currency,
        ]

        res_refresh = [elem.refresh_from_db() for elem in elems]
        res_assert = [make_asserts(elem) for elem in elems]

        assert res_assert, res_refresh

        release_payment.return_value = 'A555B'

        self.good_payment = Payment(**self.good_payment_data)
        self.good_payment.save()

        # apply task
        buy_order_release.apply()

        # reload good one from db
        self.order.refresh_from_db()
        self.good_payment.refresh_from_db()
        # test only once
        self.assertTrue(self.order.is_released)
        self.assertTrue(self.good_payment.is_redeemed)
        self.assertTrue(self.good_payment.is_complete)
        self.assertEqual(1, release_payment.call_count)

    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_set_user_on_match(self, send_email, send_sms, release_payment):
        release_payment.return_value = 'A555B'
        self.good_payment = Payment(**self.good_payment_data)
        self.good_payment.save()

        buy_order_release.apply()

        p = Payment.objects.get(pk=self.good_payment.pk)
        self.assertEqual(p.payment_preference.user,
                         self.order.user)
        self.assertEqual(p.user, self.order.user)

    def test_send_notification(self):
        pass

    # TODO: move to utils tests (validate_payment)
    def test_release_fail_payment_other_user(self):
        pass

    def test_release_fail_other_currency(self):
        pass
