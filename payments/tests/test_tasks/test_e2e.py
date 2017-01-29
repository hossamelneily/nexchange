from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from payments.tasks.generic.payeer import PayeerPaymentChecker

from core.tests.base import OrderBaseTestCase
from orders.models import Order
from payments.models import Payment, PaymentPreference
from payments.tasks.generic.ok_pay import OkPayPaymentChecker


class WalletAPITestCase(OrderBaseTestCase):
    fixtures = [
        'currency.json',
        'payment_method.json',
        'payment_preference.json',
    ]

    @classmethod
    def setUpClass(cls):
        u, created = User.objects.get_or_create(
            username='onit'
        )
        # ensure staff status, required for tests
        u.is_staff = True
        u.save()
        super(WalletAPITestCase, cls).setUpClass()

    def setUp(self):
        super(WalletAPITestCase, self).setUp()
        # look at:
        # nexchange/tests/fixtures/transaction_history.xml self.order_data
        # matches first transaction from the XML file
        pref = PaymentPreference.objects.get(
            user__is_staff=True,
            payment_method__name__icontains='okpay'
        )
        self.order_data = {
            'amount_cash': 85.85,
            'amount_btc': Decimal(0.01),
            'currency': self.EUR,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': pref,
        }

    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI.get_date_time')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    def test_confirm_order_payment_with_okpay_celery(self, history, datetime,
                                                     convert_to_cash):
        with open('nexchange/tests/fixtures/'
                  'okpay/transaction_history.xml') as f:
            history.return_value = str.encode(f.read().replace('\n', ''))
        datetime.return_value = '2017-01-11-10:00'
        convert_to_cash.return_value = None
        order = Order(**self.order_data)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()

        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))
        self.assertEqual(pref[0].identifier, 'dobbscoin@gmail.com')
        self.assertEqual(pref[0].secondary_identifier, 'OK487565544')
        # apply second time - should not create another payment
        import_okpay_payments.run()

        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        # check that pref is intact
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))
        self.assertEqual(pref[0].identifier, 'dobbscoin@gmail.com')
        self.assertEqual(pref[0].secondary_identifier, 'OK487565544')

    @patch('nexchange.utils.PayeerAPIClient.history_of_transactions')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_import_payeer__invalid_wallet(self, convert_to_cash, trans_hist):
        convert_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        trans_hist.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.order_data['amount_cash']),
                'to': 'tata',
                'shopOrderId': self.order_data['unique_reference'],
                'comment': self.order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(0, len(p))
        # assert payment pref is created correctly

    @patch('nexchange.utils.PayeerAPIClient.history_of_transactions')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_import_payeer_invalid_status(self, convert_to_cash, trans_hist):
        convert_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        trans_hist.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'None',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.order_data['amount_cash']),
                'to': 'tata',
                'shopOrderId': self.order_data['unique_reference'],
                'comment': self.order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(0, len(p))
        # assert payment pref is created correctly

    @patch('nexchange.utils.PayeerAPIClient.history_of_transactions')
    @patch('orders.models.Order.convert_coin_to_cash')
    def test_confirm_order_payment_with_payeer_celery(self, convert_to_cash,
                                                      trans_hist):
        convert_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        trans_hist.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.order_data['amount_cash']),
                'to': settings.PAYEER_ACCOUNT,
                'shopOrderId': self.order_data['unique_reference'],
                'comment': self.order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        # assert payment pref is created correctly
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))

        self.assertEquals(pref[0].identifier,
                          sender)

        # apply second time - should not create another payment\payment
        # preference
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))

        self.assertEquals(pref[0].identifier,
                          sender)
