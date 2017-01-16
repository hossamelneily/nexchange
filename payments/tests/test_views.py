
from decimal import Decimal
from unittest import skip

from core.models import Address, Transaction
from core.tests.base import OrderBaseTestCase, UserBaseTestCase
from nexchange.utils import release_payment
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from nexchange.tasks import check_okpay_payments
from unittest.mock import patch, MagicMock


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


# tests for okpay IPN
# class OkpayTestCase(UserBaseTestCase):
#
#     def setUp(self):
#         self.okpay_checkout_msg = (
#             'ok_charset=utf-8&ok_receiver=OK702746927&ok_receiver_id=666146284&'
#             'ok_receiver_wallet=OK702746927&ok_txn_id=1959454&ok_txn_kind=payme'
#             'nt_link&ok_txn_payment_type=instant&ok_txt_payment_method=OKB&ok_'
#             'txn_gross=19.95&ok_txn_amount=19.95&ok_txn_net=19.95&ok_txn_fee='
#             '0.00&ok_txn_currency=EUR&ok_txn_datetime=2013-06-01 04:18:32&'
#             'ok_txn_status=completed&ok_invoice=9&ok_payer_status=unverified&'
#             'ok_payer_id=654347086&ok_payer_reputation=0&ok_payer_first_name='
#             'John&ok_payer_last_name=Doe&ok_payer_email=client@domain.com&'
#             'ok_items_count=1&ok_item_1_name=OKPAY Poster&ok_item_1_type='
#             'digital&ok_item_1_quantity=1&ok_item_1_gross=19.95&'
#             'ok_item_1_price=19.95'
#         )
#         self.success_url = reverse('payments.success',
#                                    kwargs={'provider': 'okpay'})
#
#     def test_okpay_success(self):
#         r = self.client.post(self.success_url + self.okpay_checkout_msg)
#         self.assertEqual(200, r.status_code)

class OkpayTestCase(UserBaseTestCase):

    def setUp(self):
        super(OkpayTestCase, self).setUp()
        # need to create transaction history mock
        class HistoryInfo:
            pass
        transaction_history = HistoryInfo()
        transaction_history.transaction = MagicMock(return_value='smth smth')
        patcher = patch('nexchange.utils.OkPayAPI.get_transaction_history',
                        return_value=transaction_history)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_true(self):
        check_okpay_payments()
