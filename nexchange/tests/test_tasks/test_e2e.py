from core.tests.utils import get_ok_pay_mock
from core.tests.base import WalletBaseTestCase
from orders.models import Order
from payments.models import Payment
from unittest.mock import patch
import requests_mock
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from accounts.tests.base import TransactionImportBaseTestCase
from accounts.task_summary import import_transaction_deposit_btc_invoke
from orders.task_summary import sell_order_release_invoke, buy_order_release_by_reference_invoke, \
    buy_order_release_by_wallet_invoke, buy_order_release_by_rule_invoke
from django.conf import settings
from decimal import Decimal
import json
import os


class OKPayEndToEndTestCase(WalletBaseTestCase):
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_fail_release_no_address(self, send_email,
                                     send_sms, release_payment,
                                     _get_transaction_history,
                                     convert_coin_to_cash):
        # Purge
        Payment.objects.all().delete()
        release_payment.return_value = 'TX123'
        convert_coin_to_cash.return_value = None
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply()
        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(False, order.is_released)

    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_success_release(self, send_email, send_sms, release_payment,
                             _get_transaction_history,
                             convert_coin_to_cash):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        convert_coin_to_cash.return_value = None
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data_address)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()
        p = Payment.objects.get(
            amount_cash=order.amount_cash,
            currency=order.currency,
            reference=order.unique_reference
        )

        buy_order_release_by_reference_invoke.apply([p.pk])
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
    @patch('nexchange.utils.PayeerAPIClient.get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_failure_release_no_address(self, send_email, send_sms,
                                        release_payment,
                                        convert_coin_to_cash,
                                        transaction_history):
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

        buy_order_release_by_reference_invoke.apply([p.pk])

        p.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(False, order.is_released)

    @patch('nexchange.utils.PayeerAPIClient.get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_success_release(self, send_email, send_sms,
                             release_payment,
                             convert_coin_to_cash,
                             transaction_history):
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

        buy_order_release_by_reference_invoke.apply([p.pk])

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


class SellOrderReleaseTaskTestCase(TransactionImportBaseTestCase):
    def setUp(self):
        self.confirmation_list = [settings.MIN_REQUIRED_CONFIRMATIONS,
                                  settings.MIN_REQUIRED_CONFIRMATIONS - 1]
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_btc_invoke
        self.release_task = sell_order_release_invoke

    def _create_second_order(self):
        self.order_2 = Order(
            order_type=Order.SELL,
            amount_btc=Decimal(str(self.amounts[self.status_bad_list_index])),
            currency=self.EUR,
            user=self.user,
            is_completed=False,
            is_paid=False
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
    @patch('orders.models.Order.send_money')
    def test_release_sell_order_confirmations(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = True
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertTrue(order.is_released)

    @requests_mock.mock()
    @patch('orders.models.Order.send_money')
    def test_do_not_release_sell_order_not_enough_confirmations(self, m,
                                                                send_money):
        self.confirmation_list[0] = settings.MIN_REQUIRED_CONFIRMATIONS - 1
        self._read_fixture()
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = True
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertFalse(order.is_released)

    @requests_mock.mock()
    @patch('orders.models.Order.send_money')
    def test_sell_order_release_1_yes_1_no_due_to_confirmations(self, m,
                                                                send_money):
        self.confirmation_list = [settings.MIN_REQUIRED_CONFIRMATIONS,
                                  settings.MIN_REQUIRED_CONFIRMATIONS - 1]
        self._read_fixture()
        self._create_second_order()
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = True
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        order_2 = Order.objects.get(unique_reference=self.unique_ref_2)
        self.assertTrue(order.is_released)
        self.assertFalse(order_2.is_released)

    @requests_mock.mock()
    @patch('orders.models.Order.send_money')
    def test_do_not_release_sell_order_with_task_not_send_money(self, m,
                                                                send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = False
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertFalse(order.is_released)

    @requests_mock.mock()
    @patch('orders.models.Order.send_money')
    def test_notify_admin_if_not_send_money(self, m, send_money):
        m.get(self.url, text=self.blockr_response)
        send_money.return_value = False
        self.import_txs_task.apply()
        with self.assertRaises(NotImplementedError):
            self.release_task()
