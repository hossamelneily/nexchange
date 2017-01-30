from core.tests.utils import get_ok_pay_mock
from core.tests.base import WalletBaseTestCase
from orders.models import Order
from payments.models import Payment
from unittest.mock import patch
from payments.tasks.import_payments import OkPayPaymentChecker, \
    PayeerPaymentChecker
from orders.tasks.order_release import buy_order_release
from django.conf import settings


class OKPayEndToEndTestCase(WalletBaseTestCase):
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI.get_date_time')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_fail_release_no_address(self, send_email,
                                     send_sms, release_payment,
                                     _get_transaction_history, get_date_time,
                                     convert_coin_to_cash):
        # Purge
        Payment.objects.all().delete()
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        _get_transaction_history.return_value = get_ok_pay_mock()
        get_date_time.return_value = '2017-01-11-10:00'
        order = Order(**self.okpay_order_data)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release.apply()
        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(False, order.is_released)

    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI.get_date_time')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_success_release(self, send_email, send_sms, release_payment,
                             _get_transaction_history, get_date_time,
                             convert_coin_to_cash):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        convert_coin_to_cash.return_value = None
        _get_transaction_history.return_value = get_ok_pay_mock()
        get_date_time.return_value = '2017-01-11-10:00'
        order = Order(**self.okpay_order_data_address)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release.apply()
        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)
        self.assertEqual(True, order.is_released)

    def test_success_release_no_ref(self):
        pass

    def test_failure_release_other_pref(self):
        pass

    def test_failure_release_invalid_currency(self):
        pass

    def test_failure_release_invalid_user(self):
        pass


class PayeerEndToEndTestCase(WalletBaseTestCase):
    @patch('nexchange.utils.PayeerAPIClient.history_of_transactions')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_failure_release_no_address(self, send_email, send_sms,
                                        release_payment,
                                        convert_coin_to_cash,
                                        history_of_transactions):
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        history_of_transactions.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.payeer_order_data['amount_cash']),
                'to': settings.PAYEER_ACCOUNT,
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.payeer_order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release.apply()

        p.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(False, order.is_released)

    @patch('nexchange.utils.PayeerAPIClient.history_of_transactions')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.order_release.release_payment')
    @patch('orders.tasks.order_release.send_sms')
    @patch('orders.tasks.order_release.send_email')
    def test_success_release(self, send_email, send_sms,
                             release_payment,
                             convert_coin_to_cash,
                             history_of_transactions):
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        history_of_transactions.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.payeer_order_data['amount_cash']),
                'to': settings.PAYEER_ACCOUNT,
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.payeer_order_data_address)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release.apply()

        p.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)
        self.assertEqual(True, order.is_released)

    def test_success_release_no_ref(self):
        pass

    def test_failure_release_other_pref(self):
        pass

    def test_failure_release_invalid_currency(self):
        pass

    def test_failure_release_invalid_user(self):
        pass
