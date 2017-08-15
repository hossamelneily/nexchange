import json
from decimal import Decimal
from random import randint
from time import time

import requests_mock
from django.conf import settings
from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke
from core.models import Address, Transaction, Currency
from core.tests.base import TransactionImportBaseTestCase
from core.tests.base import UPHOLD_ROOT
from core.tests.base import WalletBaseTestCase
from core.tests.utils import data_provider
from core.tests.utils import get_ok_pay_mock, get_payeer_mock
from orders.models import Order
from orders.task_summary import sell_order_release_invoke, \
    buy_order_release_by_reference_invoke, exchange_order_release_invoke, \
    exchange_order_release_periodic, buy_order_release_by_wallet_invoke, \
    buy_order_release_by_rule_invoke
from payments.models import Payment, PaymentPreference
from payments.task_summary import run_adv_cash
from payments.task_summary import run_okpay, run_sofort
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from payments.tests.test_api_clients.base import BaseSofortAPITestCase
from ticker.tests.base import TickerBaseTestCase
from verification.models import Verification
from payments.tests.test_api_clients.test_adv_cash import \
    BaseAdvCashAPIClientTestCase
from unittest import skip


class OKPayEndToEndTestCase(WalletBaseTestCase):
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
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
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
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
    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
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
    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
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
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.release_task = sell_order_release_invoke
        self.payeer_url = settings.PAYEER_API_URL
        self.order_2 = None
        self._create_mocks_uphold()

    def _create_second_order(self):
        self.order_2 = Order(
            order_type=Order.SELL,
            amount_base=Decimal('0.04'),
            pair=self.BTCEUR,
            user=self.user,
            status=Order.INITIAL,
            payment_preference=self.main_pref
        )
        self.order_2.save()

    @skip('Sell order depreciated')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('orders.utils.send_money')
    def test_release_sell_order(self, send_money, get_txs, get_rtx):
        # TODO: generalise
        send_money.return_value = True
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_SUCCESS_RELEASED)
        t1 = self.order.transactions.first()
        self.assertEqual(t1.type, Transaction.DEPOSIT)
        self.assertEqual(t1.amount, self.order.amount_base)
        self.assertEqual(t1.currency, self.order.pair.base)

    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_do_not_release_sell_order_transaction_pending(self, get_txs,
                                                           get_rtx):
        # TODO: generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.pending)

        self.import_txs_task.apply()
        self.release_task.apply()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)

    @skip('Sell order depreciated')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('orders.utils.send_money')
    def test_sell_order_release_1_yes_1_no_due_to_confirmations(self,
                                                                send_money,
                                                                get_txs,
                                                                get_rtx):
        def side_effect(trans):
            if trans == txs_data[0]['id']:
                return json.loads(self.completed)
            elif trans == txs_data[1]['id']:
                return json.loads(self.pending)
        self._create_second_order()
        self._create_mocks_uphold(amount2=self.order_2.amount_base)
        txs_data = json.loads(self.import_txs)

        # TODO: generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.pending)

        send_money.return_value = True
        self.import_txs_task.apply()
        get_rtx.side_effect = side_effect
        self.update_confirmation_task()
        self.release_task()
        self.order.refresh_from_db()
        self.order_2.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED)
        self.assertNotIn(self.order_2.status, Order.IN_RELEASED)

    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('orders.utils.send_money')
    def test_do_not_release_sell_order_without_send_money(self, send_money,
                                                          get_txs,
                                                          get_rtx):
        # TODO: generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.pending)

        send_money.return_value = False
        self.import_txs_task.apply()
        self.release_task.apply()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)

    @skip('Sell order depreciated')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('payments.api_clients.ok_pay.OkPayAPI.send_money')
    def test_notify_admin_if_not_send_money(self, send_money, get_txs,
                                            get_rtx):

        # TODO: generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        send_money.return_value = {'error': 'smth bad'}
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()

        self.order.refresh_from_db()
        self.assertTrue(self.order.flagged)

    @skip('Sell order depreciated')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('payments.api_clients.ok_pay.OkPayAPI._send_money')
    def test_okpay_send_money_sell_order(self, send_money,
                                         get_txs, get_rtx):
        # TODO: move to base, generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        self.order.payment_preference = self.okpay_pref
        self.order.save()
        send_money.return_value = get_ok_pay_mock(
            data='transaction_send_money'
        )
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()

        self.assertEqual(1, send_money.call_count)
        self.assertIn(self.order.status, Order.IN_RELEASED)

    @skip('Sell order depreciated')
    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('payments.api_clients.payeer.PayeerAPIClient.transfer_funds')
    def test_payeer_send_money_sell_order(self, m, send_money,
                                          get_txs, get_rtx):
        # TODO: move to base, generalise, trx = reserve tx
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        m.get(self.payeer_url, text=get_payeer_mock('transfer_funds'))
        self.mock_empty_transactions_for_blockchain_address(m)
        self.order.payment_preference = self.payeer_pref
        self.order.save()
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()

        self.assertEqual(1, send_money.call_count)
        self.assertIn(self.order.status, Order.IN_RELEASED)

    @skip('Sell order depreciated')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_unknown_method_do_not_send_money_sell_order(self,
                                                         get_txs,
                                                         get_rtx):
        # TODO: move to base, generalise
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        payment_method = self.main_pref.payment_method
        payment_method.name = 'Some Random Name'
        payment_method.save()
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()

        self.order.refresh_from_db()
        self.assertTrue(self.order.flagged)
        self.assertNotIn(self.order.status, Order.IN_SUCCESS_RELEASED)
        self.assertEqual(self.order.status, Order.FAILED_RELEASE)


class SellOrderReleaseFromViewTestCase(WalletBaseTestCase):
    def setUp(self):
        super(SellOrderReleaseFromViewTestCase, self).setUp()

        self.addr_data = {
            'type': 'W',
            'name': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            'address': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            'currency': self.BTC

        }
        self.addr = Address(**self.addr_data)
        self.addr.user = self.user
        self.addr.save()

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_release_if_paid_and_withdraaw_address_set(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, convert_coin_to_cash, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
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
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        response = self.client.post(url, {
            'pk': order.pk,
            'value': self.addr.pk,
        })

        self.assertEquals(200, response.status_code)

        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)
        self.assertIn(order.status, Order.IN_RELEASED)
        self.assertEquals(1, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_withdraw_address_already_set(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, convert_coin_to_cash, validate):
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
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        response = self.client.post(url, {
            'pk': order.pk,
            'value': self.addr.pk,
        })

        self.assertEquals(200, response.status_code)

        p.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(False, p.is_complete)
        self.assertEqual(False, p.is_redeemed)
        self.assertEqual(Order.PAID, order.status)
        self.assertEquals(0, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_no_payment(self, send_email,
                                     send_sms,
                                     release_payment,
                                     _get_transaction_history,
                                     convert_coin_to_cash,
                                     validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        convert_coin_to_cash.return_value = None
        validate.return_value = True
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data)
        order.save()
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        response = self.client.post(url, {
            'pk': order.pk,
            'value': self.addr.pk,
        })

        self.assertEquals(200, response.status_code)
        order.refresh_from_db()
        self.assertEqual(Order.INITIAL, order.status)
        self.assertEquals(0, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_withdraaw_address_set_no_payment(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, convert_coin_to_cash, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        convert_coin_to_cash.return_value = None
        validate.return_value = True
        _get_transaction_history.return_value = get_ok_pay_mock()
        order = Order(**self.okpay_order_data_address)
        order.save()
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        response = self.client.post(url, {
            'pk': order.pk,
            'value': self.addr.pk,
        })

        self.assertEquals(200, response.status_code)
        order.refresh_from_db()
        self.assertEqual(Order.INITIAL, order.status)
        self.assertEquals(0, release_payment.call_count)


class BuyOrderReleaseTaskTestCase(TransactionImportBaseTestCase,
                                  WalletBaseTestCase):
    def setUp(self):
        super(BuyOrderReleaseTaskTestCase, self).setUp()
        self.update_confirmation_task = update_pending_transactions_invoke
        self.address.type = Address.WITHDRAW
        self.address.save()
        url_sandbox = 'https://api-sandbox.uphold.com'
        card1 = settings.API1_ID_C1
        self.url_prep_txn = '{}/v0/me/cards/{}/transactions'.format(
            url_sandbox, card1
        )
        self.url_commit_txn = (
            '{}/v0/me/cards/{}/transactions/{}/commit'.format(
                url_sandbox, card1, self.uphold_tx_id
            )
        )
        self.url_uphold_reverse = (
            '{}/v0/reserve/transactions/{}'.format(url_sandbox,
                                                   self.uphold_tx_id))

    def base_mock_buy_order_to_release(self, transaction_history,
                                       validate_paid, prepare_txn, execute_txn
                                       ):
        transaction_history.return_value = get_ok_pay_mock()
        validate_paid.return_value = True

        prepare_txn.return_value = 'txid12345'
        execute_txn.return_value = True
        # Create order
        self.okpay_order_data['withdraw_address'] = self.address
        order = Order(**self.okpay_order_data)
        order.save()
        self.assertEqual(order.status, Order.INITIAL)

        # Import Payment
        run_okpay.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)

        # Release Order
        payment = Payment.objects.get(reference=order.unique_reference)
        buy_order_release_by_reference_invoke.apply([payment.pk])
        order.refresh_from_db()
        self.assertEqual(order.status, Order.RELEASED)
        return order

    # TODO: change patch to request_mock (some problems with Uphold mocking
    # while running all the tests)
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    def test_complete_buy_order(self, transaction_history, validate_paid,
                                prepare_txn, execute_txn, reserve_txn):
        order = self.base_mock_buy_order_to_release(
            transaction_history, validate_paid, prepare_txn, execute_txn
        )

        # Check transaction status (Completed)
        reserve_txn.return_value = {'status': 'completed'}
        self.update_confirmation_task.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.COMPLETED)

    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    def test_pending_tx_not_completed_buy_order(self, transaction_history,
                                                validate_paid, prepare_txn,
                                                execute_txn, reserve_txn):
        order = self.base_mock_buy_order_to_release(
            transaction_history, validate_paid, prepare_txn, execute_txn
        )

        # Check transaction status (Pending)
        reserve_txn.return_value = {'status': 'pending'}
        self.update_confirmation_task.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.RELEASED)


class ExchangeOrderReleaseTaskTestCase(TransactionImportBaseTestCase,
                                       TickerBaseTestCase):

    def setUp(self):
        super(ExchangeOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.release_task = exchange_order_release_invoke
        self.release_task_periodic = exchange_order_release_periodic

    @data_provider(
        lambda: (
            ('ETHLTC', Order.BUY, False),
            ('BTCETH', Order.BUY, False),
            ('BTCLTC', Order.BUY, True),
            ('ETHLTC', Order.SELL, True),
            ('BTCETH', Order.SELL, False),
            ('BTCLTC', Order.SELL, True),
            ('BTCRNS', Order.BUY, True),
            ('LTCRNS', Order.BUY, True),
        )
    )
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.release_coins')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_release_exchange_order(self, pair_name, order_type,
                                    release_with_periodic,
                                    check_tx_uphold,
                                    get_txs_uphold,
                                    prepare_txn_uphold,
                                    execute_txn_uphold,
                                    get_txs_scrypt, get_tx_scrypt,
                                    release_coins_scrypt):
        currency_quote_code = pair_name[3:]
        currency_base_code = pair_name[0:3]
        self._create_order(order_type=order_type, pair_name=pair_name)
        if order_type == Order.BUY:
            mock_currency_code = currency_quote_code
            mock_amount = self.order.amount_quote
            withdraw_currency_code = currency_base_code
        else:
            # order_type == Order.SELL
            mock_currency_code = currency_base_code
            mock_amount = self.order.amount_base
            withdraw_currency_code = currency_quote_code
        mock_currency = Currency.objects.get(code=mock_currency_code)

        card = self.order.deposit_address.reserve
        card.need_balance_check = False
        card.save()

        if mock_currency.wallet == 'api1':
            card_id = card.card_id
            get_txs_uphold.return_value = [
                self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
            ]
        else:
            get_txs_scrypt.return_value = [{
                'address': card.address,
                'category': 'receive',
                'account': '',
                'amount': mock_amount,
                'txid': 'txid_{}{}'.format(time(), randint(1, 999)),
                'confirmations': 0,
                'timereceived': 1498736269,
                'time': 1498736269,
                'fee': Decimal('-0.00000100')
            }]
        check_tx_uphold.return_value = True
        get_tx_scrypt.return_value = {'confirmations': 249}
        self.import_txs_task.apply()
        prepare_txn_uphold.return_value = release_coins_scrypt.return_value = \
            'txid_{}{}'.format(time(), randint(1, 999))
        execute_txn_uphold.return_value = True

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        if mock_currency.wallet == 'api1':
            card.refresh_from_db()
            self.assertTrue(card.need_balance_check)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        tx_pk = Transaction.objects.last().pk
        address = getattr(self, '{}_address'.format(withdraw_currency_code))
        self._update_withdraw_address(self.order, address)
        if release_with_periodic:
            self.release_task_periodic.apply()
        else:
            self.release_task.apply([tx_pk])
        self.order.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED, pair_name)
        t1 = self.order.transactions.first()
        t2 = self.order.transactions.last()
        self.assertEqual(t1.type, Transaction.DEPOSIT, pair_name)
        self.assertEqual(t2.type, Transaction.WITHDRAW, pair_name)
        if order_type == Order.BUY:
            t_quote = t1
            t_base = t2
        else:
            t_quote = t2
            t_base = t1
        self.assertEqual(t_quote.amount, self.order.amount_quote, pair_name)
        self.assertEqual(t_base.amount, self.order.amount_base, pair_name)
        self.assertEqual(t_quote.currency, self.order.pair.quote, pair_name)
        self.assertEqual(t_base.currency, self.order.pair.base, pair_name)

    @data_provider(
        lambda: (
            ('ETHLTC',),
            ('ETHRNS',),
            ('BTCLTC',),
            ('BTCETH',),
        )
    )
    @patch('orders.models.Order.expired')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient.release_coins')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_not_released_expired_exchange_order(self, pair_name,
                                                 check_tx_uphold,
                                                 get_txs_uphold,
                                                 prepare_txn_uphold,
                                                 execute_txn_uphold,
                                                 get_txs_scrypt, get_tx_scrypt,
                                                 release_coins_scrypt,
                                                 order_expired):
        order_expired.return_value = True
        currency_quote_code = pair_name[3:]
        self._create_order(pair_name=pair_name)
        mock_currency_code = currency_quote_code
        mock_amount = self.order.amount_quote
        mock_currency = Currency.objects.get(code=mock_currency_code)

        card = self.order.deposit_address.reserve
        card.need_balance_check = False
        card.save()

        if mock_currency.wallet == 'api1':
            card_id = card.card_id
            get_txs_uphold.return_value = [
                self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
            ]
        else:
            get_txs_scrypt.return_value = [{
                'address': card.address,
                'category': 'receive',
                'account': '',
                'amount': mock_amount,
                'txid': 'txid_{}{}'.format(time(), randint(1, 999)),
                'confirmations': 0,
                'timereceived': 1498736269,
                'time': 1498736269,
                'fee': Decimal('-0.00000100')
            }]
        check_tx_uphold.return_value = True
        get_tx_scrypt.return_value = {'confirmations': 249}
        self.import_txs_task.apply()
        prepare_txn_uphold.return_value = release_coins_scrypt.return_value = \
            'txid_{}{}'.format(time(), randint(1, 999))
        execute_txn_uphold.return_value = True

        self.order.refresh_from_db()
        self.assertTrue(self.order.expired)
        self.assertNotEquals(self.order.status, Order.PAID_UNCONFIRMED,
                             pair_name)
        self.assertEqual(self.order.status, Order.INITIAL, pair_name)


class SofortEndToEndTestCase(BaseSofortAPITestCase,
                             TransactionImportBaseTestCase,
                             TickerBaseTestCase):

    def setUp(self):
        super(SofortEndToEndTestCase, self).setUp()
        self.payments_importer = run_sofort
        self.sender_name = 'Sender Awesome'
        self.iban = 'DE86000000002345678902'
        self.transaction_data = {
            'sender_name': self.sender_name,
            'iban': self.iban
        }

    @data_provider(lambda: (
        ('BTCEUR',),
        ('ETHEUR',),
        ('LTCEUR',),
    ))
    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_success_release(self, pair_name, mock, prepare_txn, execute_txn,
                             get_txs, get_rtx):
        # Less then 1.0 fiat payments is blocked by PaymentChecker validator
        self._mock_cards_reserve(mock)
        self._create_order(amount_base=2.0, pair_name=pair_name,
                           payment_preference=self.sofort_pref)

        self._create_mocks_uphold()
        get_rtx.return_value = json.loads(self.completed)

        self.transaction_data.update({
            'order_id': self.order.unique_reference,
            'amount': self.order.amount_quote,
            'currency': self.order.pair.quote.code,
            'transaction_id': str(time())
        })
        transaction_xml = self.create_transaction_xml(
            **self.transaction_data
        )
        self.mock_transaction_history(mock, transaction_xml)
        self.payments_importer.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        p = Payment.objects.get(
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote,
            reference=self.order.unique_reference
        )

        prepare_txn.return_value = str(time())
        execute_txn.return_value = True
        get_txs.return_value = json.loads(self.import_txs)
        address = getattr(self, '{}_address'.format(pair_name[:3]))
        self._update_withdraw_address(self.order, address)

        buy_order_release_by_reference_invoke.apply([p.pk])
        p.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(True, p.is_complete)
        self.assertEqual(True, p.is_redeemed)

        self.assertEqual(self.order.status, Order.COMPLETED)
        t1 = self.order.transactions.first()
        self.assertEqual(t1.type, Transaction.WITHDRAW, pair_name)
        self.assertEqual(t1.amount, self.order.amount_base, pair_name)
        self.assertEqual(t1.currency, self.order.pair.base, pair_name)

    @data_provider(lambda: (
        (buy_order_release_by_reference_invoke,),
        (buy_order_release_by_wallet_invoke,),
        (buy_order_release_by_rule_invoke,),
    ))
    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_do_not_release_unverified(self, release_task, mock, prepare_txn,
                                       execute_txn, reserve_txn):
        self._create_order(amount_base=2.0, pair_name='BTCEUR',
                           payment_preference=self.sofort_pref)
        self.sofort_pref.required_verification_buy = True
        self.sofort_pref.save()
        self.transaction_data.update({
            'order_id': self.order.unique_reference,
            'amount': self.order.amount_quote,
            'currency': self.order.pair.quote.code,
            'transaction_id': str(time())
        })
        transaction_xml = self.create_transaction_xml(
            **self.transaction_data
        )
        self.mock_transaction_history(mock, transaction_xml)
        self.payments_importer.apply()
        payment = Payment.objects.get(
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote,
            reference=self.order.unique_reference
        )
        verifications = Verification.objects.filter(user=payment.user)
        for ver in verifications:
            ver.id_status = Verification.REJECTED
            ver.util_status = Verification.REJECTED
            ver.save()
        prepare_txn.return_value = str(time())
        execute_txn.return_value = True
        reserve_txn.return_value = {'status': 'completed'}
        self.order.refresh_from_db()
        self.order.withdraw_address = Address.objects.filter(
            type=Address.WITHDRAW, currency=self.BTC)[0]
        self.order.save()

        release_task.apply([payment.pk])

        self.order.refresh_from_db()

        self.assertNotIn(self.order.status, Order.IN_SUCCESS_RELEASED)
        self.assertEqual(self.order.status, Order.PAID)


class AdvCashE2ETestCase(BaseAdvCashAPIClientTestCase,
                         TransactionImportBaseTestCase):
    def setUp(self):
        super(AdvCashE2ETestCase, self).setUp()
        self.order.order_type = Order.SELL
        self.payment_importer = run_adv_cash
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.user.email = "Sir@test.alot"
        self.user.save()
        self.completed = '{"status": "completed", "type": "deposit"}'

    @data_provider(lambda: (
        ('BUY BTCEUR', 'BTCEUR', Order.BUY),
    ))
    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_success_release(self, name, pair_name, order_type, mock,
                             history_patch, prepare_txn, execute_txn, get_txs,
                             get_rtx):
        self._mock_cards_reserve(mock)
        self._create_order(amount_base=2.0, pair_name=pair_name,
                           payment_preference=self.adv_cash_pref,
                           order_type=order_type)
        self._create_mocks_uphold()
        get_rtx.return_value = json.loads(self.completed)

        txs_resp = self.mock_advcash_transaction_response(**{
            'unique_ref': self.order.unique_reference,
            'amount': self.order.amount_quote,
            'currency': self.order.pair.quote.code,
            'tx_id': str(time()),
            'dest_wallet_id': settings.ADV_CASH_WALLET_EUR,
            'receiver_email': self.adv_cash_pref.identifier,
            'sender_email': self.sender_email,
            'src_wallet_id': self.sender_wallet,
            'comment': self.order.unique_reference,
        })
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(
                transactions=txs_resp)
        self.payment_importer.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, name)
        p = Payment.objects.get(
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote,
            reference=self.order.unique_reference
        )

        prepare_txn.return_value = str(time())
        execute_txn.return_value = True
        get_txs.return_value = json.loads(self.import_txs)
        address = getattr(self, '{}_address'.format(pair_name[:3]))
        self._update_withdraw_address(self.order, address)

        # NOTE: buy_order_release_invoke is after withdraw address is set
        p.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(True, p.is_complete, name)
        self.assertEqual(True, p.is_redeemed, name)

        self.assertEqual(self.order.status, Order.COMPLETED)
        t1 = self.order.transactions.first()
        self.assertEqual(t1.type, Transaction.WITHDRAW, name)
        self.assertEqual(t1.amount, self.order.amount_base, name)
        self.assertEqual(t1.currency, self.order.pair.base, name)

    @skip('Sell order depreciated')
    @data_provider(lambda: (
        ('SELL BTCEUR', 'BTCEUR', Order.SELL),
    ))
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient._send_money')
    def test_success_release_sell(self, name, pair_name, order_type,
                                  send_money, prepare_txn, execute_txn,
                                  get_txs, get_rtx, check_txn):
        get_rtx.return_value = json.loads(self.completed)
        fiat_currency_code = pair_name[3:]
        fiat_currency = Currency.objects.get(code=fiat_currency_code)
        pref, created = \
            PaymentPreference.objects.get_or_create(
                user=self.user,
                payment_method=self.adv_cash_pref.payment_method,
                identifier=self.user.email
            )

        pref.currency.add(fiat_currency)
        pref.save()
        self._create_order(amount_base=2.0, pair_name=pair_name,
                           payment_preference=self.adv_cash_pref,
                           order_type=order_type)

        mock_currency_code = self.order.pair.base.code
        mock_amount = self.order.amount_base
        mock_currency = Currency.objects.get(code=mock_currency_code)

        card = self.order.user.addressreserve_set.get(currency=mock_currency)
        card.need_balance_check = False
        card.save()

        card_id = card.card_id
        get_txs.return_value = [
            self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
        ]
        check_txn.return_value = True
        self.import_txs_task.apply()
        tx_id = 'txid_{}{}'.format(time(), randint(1, 999))
        prepare_txn.return_value = tx_id
        execute_txn.return_value = True
        send_money.return_value = self.mock_advcash_sendmoney_response(
            tx_id=tx_id)

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        card.refresh_from_db()
        self.assertTrue(card.need_balance_check)
        self.order.refresh_from_db()

        self.order.refresh_from_db()

        self.assertEqual(self.order.status, Order.COMPLETED, name)

    @skip('Sell order depreciated')
    @data_provider(lambda: (
        ('SELL BTCEUR flaged', 'BTCEUR', Order.SELL),
    ))
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.send_money')
    def test_success_release_sell_fail(self, name, pair_name, order_type,
                                       send_money, prepare_txn, execute_txn,
                                       get_txs, get_rtx, check_txn):
        get_rtx.return_value = json.loads(self.completed)
        fiat_currency_code = pair_name[3:]
        fiat_currency = Currency.objects.get(code=fiat_currency_code)
        pref, created = \
            PaymentPreference.objects.get_or_create(
                user=self.user,
                payment_method=self.adv_cash_pref.payment_method,
                identifier=self.user.email
            )

        pref.currency.add(fiat_currency)
        pref.save()
        self._create_order(amount_base=2.0, pair_name=pair_name,
                           payment_preference=self.adv_cash_pref,
                           order_type=order_type)

        mock_currency_code = self.order.pair.base.code
        mock_amount = self.order.amount_base

        card = self.order.despoit_address.reserve
        card.need_balance_check = False
        card.save()

        card_id = card.card_id
        get_txs.return_value = [
            self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
        ]
        check_txn.return_value = True
        self.import_txs_task.apply()
        tx_id = 'txid_{}{}'.format(time(), randint(1, 999))
        prepare_txn.return_value = tx_id
        execute_txn.return_value = True
        send_money.return_value = {'status': 'ERROR'}
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.FAILED_RELEASE, name)
        self.assertTrue(self.order.flagged, name)
