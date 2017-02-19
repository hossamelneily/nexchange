from core.tests.utils import get_ok_pay_mock, get_payeer_pay_mock
from core.tests.base import WalletBaseTestCase
from orders.models import Order
from payments.models import Payment
from unittest.mock import patch
import requests_mock
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from core.tests.base import TransactionImportBaseTestCase
from accounts.task_summary import import_transaction_deposit_btc_invoke
from orders.task_summary import sell_order_release_invoke,\
    buy_order_release_by_reference_invoke
from django.conf import settings
from decimal import Decimal
import json
import os


class OKPayEndToEndTestCase(WalletBaseTestCase):
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_fail_release_no_address(self, send_email,
                                     send_sms, release_payment,
                                     _get_transaction_history,
                                     convert_coin_to_cash, validate):
        # Purge
        Payment.objects.all().delete()
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        validate.return_value = True
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply()
        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(Order.PAID, order.status)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_success_release(self, send_email, send_sms, release_payment,
                             _get_transaction_history,
                             convert_coin_to_cash, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        convert_coin_to_cash.return_value = None
        validate.return_value = True
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data_address)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply([p.pk])
        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)
        self.assertEqual(Order.RELEASED, order.status)

    def test_success_release_no_ref(self):
        pass

    def test_failure_release_other_pref(self):
        pass

    def test_failure_release_invalid_currency(self):
        pass

    def test_failure_release_invalid_user(self):
        pass


class PayeerEndToEndTestCase(WalletBaseTestCase):
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('nexchange.utils.PayeerAPIClient.get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_failure_release_no_address(self, send_email, send_sms,
                                        release_payment,
                                        convert_coin_to_cash,
                                        transaction_history, validate):
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        transaction_history.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.payeer_order_data['amount_quote']),
                'to': settings.PAYEER_ACCOUNT,
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        validate.return_value = True
        order = Order(**self.payeer_order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply([p.pk])

        p.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(Order.PAID, order.status)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('nexchange.utils.PayeerAPIClient.get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_success_release(self, send_email, send_sms,
                             release_payment,
                             convert_coin_to_cash,
                             transaction_history, validate):
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        transaction_history.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.payeer_order_data['amount_quote']),
                'to': settings.PAYEER_ACCOUNT,
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        validate.return_value = True
        order = Order(**self.payeer_order_data_address)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply([p.pk])

        p.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)
        self.assertEqual(True, order.status == Order.RELEASED)

    def test_success_release_no_ref(self):
        pass

    def test_failure_release_other_pref(self):
        pass

    def test_failure_release_invalid_currency(self):
        pass

    def test_failure_release_invalid_user(self):
        pass


class SellOrderReleaseTaskTestCase(TransactionImportBaseTestCase):
    def setUp(self):
        self.confirmation_list = [settings.MIN_REQUIRED_CONFIRMATIONS,
                                  settings.MIN_REQUIRED_CONFIRMATIONS - 1]
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_btc_invoke
        self.release_task = sell_order_release_invoke
        self.payeer_url = settings.PAYEER_API_URL

    def _create_second_order(self):
        self.order_2 = Order(
            order_type=Order.SELL,
            amount_base=Decimal(str(self.amounts[self.status_bad_list_index])),
            pair=self.BTCEUR,
            user=self.user,
            status=Order.INITIAL,
            payment_preference=self.main_pref
        )
        self.order_2.save()
        self.unique_ref_2 = self.order_2.unique_reference

    def _read_fixture(self):
        cont_path = os.path.join(settings.BASE_DIR,
                                 'nexchange/tests/fixtures/'
                                 'blockr/address_transactions.json')
        with open(cont_path) as f:
            response = f.read().replace('\n', '').replace(' ', '')
            loads = json.loads(response)
            # change confirmation numbers
            for i, txs in enumerate(loads['data']['txs']):
                confirmations = txs['confirmations']
                response = response.replace(
                    str(confirmations),
                    str(self.confirmation_list[i])
                )

            self.wallet_address = json.loads(response)['data'][
                'address'
            ]
            self.blockr_response = response
            txs = json.loads(self.blockr_response)['data']['txs']
            self.amounts = [tx['amount'] for tx in txs]
            self.tx_ids = [tx['tx'] for tx in txs]
        self.status_ok_list_index = 0
        self.status_bad_list_index = 1

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def test_release_sell_order_confirmations(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = True
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertTrue(order.status in Order.IN_RELEASED)

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def test_do_not_release_sell_order_not_enough_confirmations(self, m,
                                                                send_money):
        self.confirmation_list[0] = settings.MIN_REQUIRED_CONFIRMATIONS - 1
        self._read_fixture()
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = True
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertNotIn(order.status, Order.IN_RELEASED)

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def test_sell_order_release_1_yes_1_no_due_to_confirmations(self, m,
                                                                send_money):
        self.confirmation_list = [settings.MIN_REQUIRED_CONFIRMATIONS,
                                  settings.MIN_REQUIRED_CONFIRMATIONS - 1]
        self._read_fixture()
        self._create_second_order()
        send_money.return_value = True
        m.get(self.url, text=self.blockr_response)
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        order_2 = Order.objects.get(unique_reference=self.unique_ref_2)
        self.assertIn(order.status, Order.IN_RELEASED)
        self.assertNotIn(order_2.status, Order.IN_RELEASED)

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def test_do_not_release_sell_order_with_task_not_send_money(self, m,
                                                                send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = False
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertNotIn(order.status, Order.IN_RELEASED)

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def test_notify_admin_if_not_send_money(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = False
        self.import_txs_task.apply()
        with self.assertRaises(NotImplementedError):
            self.release_task()

    @requests_mock.mock()
    @patch('nexchange.utils.OkPayAPI._send_money')
    def test_okpay_send_money_sell_order(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        self.order.payment_preference = self.okpay_pref
        self.order.save()
        send_money.return_value = get_ok_pay_mock(
            data='transaction_send_money'
        )
        self.import_txs_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()

        self.assertEqual(1, send_money.call_count)
        self.assertIn(self.order.status, Order.IN_RELEASED)

    @requests_mock.mock()
    @patch('nexchange.utils.PayeerAPIClient.transfer_funds')
    def test_payeer_send_money_sell_order(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        m.get(self.payeer_url, text=get_payeer_pay_mock('transfer_funds'))
        self.order.payment_preference = self.payeer_pref
        self.order.save()
        self.import_txs_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()

        self.assertEqual(1, send_money.call_count)
        self.assertIn(self.order.status, Order.IN_RELEASED)

    @requests_mock.mock()
    def test_unknown_method_do_not_send_money_sell_order(self, m):
        m.get(self.url, text=self.blockr_response)
        payment_method = self.main_pref.payment_method
        payment_method.name = 'Some Random Name'
        payment_method.save()
        self.import_txs_task.apply()
        self.release_task.apply()

        with self.assertRaises(NotImplementedError):
            self.release_task()

        self.order.refresh_from_db()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)
