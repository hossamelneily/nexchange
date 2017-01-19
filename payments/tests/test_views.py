
from decimal import Decimal
from unittest import skip
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from core.models import Address, Transaction
from core.tests.base import OrderBaseTestCase, UserBaseTestCase
from nexchange.utils import release_payment
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from payments.utils import get_payeer_sign, get_payeer_desc


class PayeerTestCase(TestCase):

    def _create_input_params(self, status='success', delete=None):
        input_list = [
            '123456',
            '2609',
            '21.12.2012 21:12',
            '21.12.2012 21:12',
            '287402376',
            '12345',
            '100.00',
            'EUR',
            get_payeer_desc('BUY 0.1BTC'),
            status,
            '12345'
        ]
        self.input_params = {
            'm_operation_id': input_list[0],
            'm_operation_ps': input_list[1],
            'm_operation_date': input_list[2],
            'm_operation_pay_date': input_list[3],
            'm_shop': input_list[4],
            'm_orderid': input_list[5],
            'm_amount': input_list[6],
            'm_curr': input_list[7],
            'm_desc': input_list[8],
            'm_status': input_list[9],
            'm_sign': get_payeer_sign(ar_hash=(i for i in input_list))
        }
        if delete is not None:
            del self.input_params[delete]

    def setUp(self):
        self.status_url = reverse('payments.payeer.status')
        self.client = Client()
        self._create_input_params()

    def test_payeer_status_success(self):
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertIn('|success', content)

    def test_payeer_status_error(self):
        self._create_input_params(status='error')
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertIn('|error', content)

    def test_payeer_status_missing_param_error(self):
        self._create_input_params(status='error', delete='m_operation_id')
        response = self.client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf8')
        self.assertEqual('error', content)


class RoboTestCase(UserBaseTestCase):

    def setUp(self):
        super(RoboTestCase, self).setUp()

    @skip("causes failures, needs to be migrated")
    def test_bad_paysuccess(self):
        r = self.client.post('/en/paysuccess/robokassa')
        self.assertEqual(r.json()['result'], 'bad request')

    @skip("causes failures, needs to be migrated")
    def test_bad_paysuccess_with_param(self):
        r = self.client.post('/en/paysuccess/robokassa',
                             {'OutSum': 1,
                              'InvId': 1,
                              'SignatureValue': 'fsdfdfdsd'})
        self.assertEqual(r.json()['result'], 'bad request')


class PaymentReleaseTestCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(PaymentReleaseTestCase, self).setUp()
        self.method_data = {
            "is_internal": 1,
            'name': 'Robokassa'
        }

        amount_cash = Decimal(30000.00)

        self.payment_method = PaymentMethod(name='ROBO')
        self.payment_method.save()

        self.addr_data = {
            'type': 'W',
            'name': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            'address': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',

        }

        self.addr = Address(**self.addr_data)
        self.addr.user = self.user
        self.addr.save()

        pref_data = {
            'user': self.user,
            'comment': 'Just testing',
            'payment_method': self.payment_method
        }

        pref = PaymentPreference(**pref_data)
        pref.save('internal')

        self.data = {
            'amount_cash': amount_cash,
            'amount_btc': Decimal(1.00),
            'currency': self.RUB,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': pref,
            'is_paid': True
        }

        self.order = Order(**self.data)
        self.order.save()

        self.pay_data = {
            'amount_cash': self.order.amount_cash,
            'currency': self.RUB,
            'user': self.user,
            'payment_preference': pref,
        }

        self.payment = Payment(**self.pay_data)
        self.payment.save()

        tx_id_ = '76aa6bdc27e0bb718806c93db66525436' \
                 'fa621766b52bad831942dee8b618678'

        self.transaction = Transaction(tx_id=tx_id_,
                                       order=self.order, address_to=self.addr)
        self.transaction.save()

    def test_bad_release_payment(self):
        for o in Order.objects.filter(is_paid=True, is_released=False):
            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_cash,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.currency).first()
            if p is not None:
                tx_id_ = release_payment(o.withdraw_address,
                                         o.amount_btc)
                self.assertEqual(tx_id_, None)

    def test_orders_with_approved_payments(self):

        for o in Order.objects.filter(is_paid=True, is_released=False):

            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_cash,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.currency).first()

            if p is not None:

                o.is_released = True
                o.save()

                p.is_complete = True
                p.save()

            self.assertTrue(o.is_released)
            self.assertTrue(p.is_complete)
