from decimal import Decimal
from unittest import skip
from unittest.mock import patch
from django.core.urlresolvers import reverse
from django.test import Client
from django.conf import settings

from core.models import Address, Transaction
from core.tests.base import OrderBaseTestCase, UserBaseTestCase
from nexchange.utils import release_payment
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from payments.utils import get_payeer_sign, get_payeer_desc


class PayeerTestCase(OrderBaseTestCase):

    def _create_input_params(self, status='success', delete=None,
                             order_id='12345'):
        input_list = [
            '123456',
            '2609',
            '21.12.2012 21:12',
            '21.12.2012 21:12',
            settings.PAYEER_WALLET,
            order_id,
            '100.00',
            'EUR',
            get_payeer_desc('BUY 0.1BTC'),
            status,
            settings.PAYEER_IPN_KEY
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
        super(PayeerTestCase, self).setUp()
        self.status_url = reverse('payments.payeer.status')
        self.client = Client(REMOTE_ADDR='185.71.65.92')
        self.payment_method = PaymentMethod(name='Payeer')
        self.payment_method.save()
        self._create_input_params()
        pref_data = {
            'comment': 'Just testing',
            'payment_method': self.payment_method,
            'user': self.user
        }
        self.pref = PaymentPreference(**pref_data)
        self.pref.save()

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

    @patch('orders.models.Order.convert_coin_to_cash')
    def test_payeer_payment_after_success(self, convert_coin):
        convert_coin.return_value = None
        order_data = {
            'amount_quote': Decimal(self.input_params['m_amount']),
            'amount_base': Decimal(0.1),
            'pair': self.BTCEUR,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': self.input_params['m_orderid'],
            'payment_preference': self.pref,
        }
        order = Order(**order_data)
        order.save()
        self._create_input_params(order_id=order.unique_reference)
        self.client.post(self.status_url, self.input_params)
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            order=order,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        # apply second time - should not create another payment
        self.client.post(self.status_url, self.input_params)
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            order=order,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))

    def test_payeer_forbidden_ip_request(self):
        client = Client(REMOTE_ADDR='127.0.0.1')
        response = client.post(self.status_url, self.input_params)
        self.assertEqual(response.status_code, 403)


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


class PaymentReleaseTestCase(OrderBaseTestCase):

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
            'comment': 'Just testing',
            'payment_method': self.payment_method,
            'user': self.user
        }

        pref = PaymentPreference(**pref_data)
        pref.save('internal')
        self.data = {
            'amount_quote': amount_cash,
            'amount_base': Decimal(1.00),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': pref,
            'status': Order.PAID
        }

        self.order = Order(**self.data)
        self.order.save()

        self.pay_data = {
            'amount_cash': self.order.amount_quote,
            'currency': self.order.pair.quote,
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

    @patch('nexchange.utils.api.prepare_txn')
    def test_bad_release_payment(self, prepare):
        for o in Order.objects.filter(status=Order.PAID):
            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_quote,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.pair.quote).first()
            if p is not None:
                tx_id_ = release_payment(o.withdraw_address,
                                         o.amount_base, 'BTC')
                self.assertEqual(tx_id_, None)

    def test_orders_with_approved_payments(self):

        for o in Order.objects.filter(status=Order.PAID):

            p = Payment.objects.filter(user=o.user,
                                       amount_cash=o.amount_quote,
                                       payment_preference=o.payment_preference,
                                       is_complete=False,
                                       currency=o.pair.quote).first()

            if p is not None:

                o.status = Order.RELEASED
                o.save()

                p.is_complete = True
                p.save()

            # Can't use refresh_from_db or o itself because 'RELEASED' is set
            #  on test itself
            order_check = Order.objects.get(
                unique_reference=o.unique_reference
            )
            self.assertTrue(order_check.status == Order.RELEASED)
            self.assertTrue(p.is_complete)
