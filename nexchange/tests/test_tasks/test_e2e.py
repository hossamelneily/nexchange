from core.tests.utils import get_ok_pay_mock, get_payeer_mock
from core.tests.base import WalletBaseTestCase
from core.models import Address, Pair, Transaction, Currency
from orders.models import Order
from payments.models import Payment, UserCards
from unittest.mock import patch
import requests_mock
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from payments.task_summary import run_okpay
from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke
from orders.task_summary import sell_order_release_invoke,\
    buy_order_release_by_reference_invoke, exchange_order_release_invoke
from django.conf import settings
from decimal import Decimal
from django.core.urlresolvers import reverse
import json
from core.tests.utils import data_provider


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
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.release_task = sell_order_release_invoke
        self.payeer_url = settings.PAYEER_API_URL
        self.order_2 = None
        self._create_mocks()

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

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('orders.utils.send_money')
    def test_release_sell_order(self, send_money, reserve_txs, import_txs):
        send_money.return_value = True
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()
        self.order.refresh_from_db()
        self.assertTrue(self.order.status in Order.IN_RELEASED)

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    def test_do_not_release_sell_order_transaction_pending(self, reserve_txs,
                                                           import_txs):
        reserve_txs.return_value = json.loads(self.pending)
        import_txs.return_value = json.loads(self.import_txs)
        self.import_txs_task.apply()
        self.release_task.apply()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('orders.utils.send_money')
    def test_sell_order_release_1_yes_1_no_due_to_confirmations(self,
                                                                send_money,
                                                                reserve_txs,
                                                                import_txs):
        def side_effect(trans):
            if trans == txs_data[0]['id']:
                return json.loads(self.completed)
            elif trans == txs_data[1]['id']:
                return json.loads(self.pending)
        self._create_second_order()
        self._create_mocks(amount2=self.order_2.amount_base)
        txs_data = json.loads(self.import_txs)
        import_txs.return_value = txs_data
        reserve_txs.return_value = json.loads(self.pending)
        send_money.return_value = True
        self.import_txs_task.apply()
        reserve_txs.side_effect = side_effect
        self.update_confirmation_task()
        self.release_task()
        self.order.refresh_from_db()
        self.order_2.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED)
        self.assertNotIn(self.order_2.status, Order.IN_RELEASED)

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('orders.utils.send_money')
    def test_do_not_release_sell_order_without_send_money(self, send_money,
                                                          reserve_txs,
                                                          import_txs):
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
        send_money.return_value = False
        self.import_txs_task.apply()
        self.release_task.apply()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('orders.utils.send_money')
    def test_notify_admin_if_not_send_money(self, send_money, reserve_txs,
                                            import_txs):
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
        send_money.return_value = False
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()

        with self.assertRaises(NotImplementedError):
            self.release_task()

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('nexchange.utils.OkPayAPI._send_money')
    def test_okpay_send_money_sell_order(self, send_money, reserve_txs,
                                         import_txs):
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
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

    @requests_mock.mock()
    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('nexchange.utils.PayeerAPIClient.transfer_funds')
    def test_payeer_send_money_sell_order(self, m, send_money, reserve_txs,
                                          import_txs):
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
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

    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    def test_unknown_method_do_not_send_money_sell_order(self, reserve_txs,
                                                         import_txs):
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
        payment_method = self.main_pref.payment_method
        payment_method.name = 'Some Random Name'
        payment_method.save()
        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.release_task.apply()

        with self.assertRaises(NotImplementedError):
            self.release_task()

        self.order.refresh_from_db()
        self.assertNotIn(self.order.status, Order.IN_RELEASED)


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
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
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
        self.assertEqual(Order.RELEASED, order.status)
        self.assertEquals(1, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
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
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
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
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    @patch('orders.tasks.generic.base.release_payment')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
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
    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('nexchange.utils.api.execute_txn')
    @patch('nexchange.utils.api.prepare_txn')
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
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

    @patch('nexchange.utils.api.get_reserve_transaction')
    @patch('nexchange.utils.api.execute_txn')
    @patch('nexchange.utils.api.prepare_txn')
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
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
        self.LTC = Currency.objects.get(code='LTC')
        self.ETH = Currency.objects.get(code='ETH')
        self.BTC_address = self._create_withdraw_adress(
            self.BTC, '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi')
        self.LTC_address = self._create_withdraw_adress(
            self.LTC, 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA')
        self.ETH_address = self._create_withdraw_adress(
            self.ETH, '0x8116546AaC209EB58c5B531011ec42DD28EdFb71')

    def _update_withdraw_address(self, order, address):
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        self.client.post(url, {
            'pk': order.pk,
            'value': address.pk,
        })

    def _create_withdraw_adress(self, currency, address):
        addr_data = {
            'type': 'W',
            'name': address,
            'address': address,
            'currency': currency

        }
        addr = Address(**addr_data)
        addr.user = self.user
        addr.save()
        return addr

    def _create_order(self, order_type=Order.BUY,
                      amount_base=0.05, pair_name='ETHLTC'):
        pair = Pair.objects.get(name=pair_name)
        # order.exchange == True if pair.is_crypto
        self.order = Order(
            order_type=order_type,
            amount_base=Decimal(str(amount_base)),
            pair=pair,
            user=self.user,
            status=Order.INITIAL
        )
        self.order.save()

    @data_provider(
        lambda: (('ETHLTC', Order.BUY,),
                 ('BTCETH', Order.BUY,),
                 ('BTCLTC', Order.BUY,),
                 ('ETHLTC', Order.SELL,),
                 ('BTCETH', Order.SELL,),
                 ('BTCLTC', Order.SELL,),
                 )
    )
    @patch('nexchange.utils.api.execute_txn')
    @patch('nexchange.utils.api.prepare_txn')
    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    def test_release_exchange_order(self, pair_name, order_type, reserve_txs,
                                    import_txs, prepare_txn, execute_txn):
        Transaction.objects.all().delete()
        currency_quote_code = pair_name[3:]
        currency_base_code = pair_name[0:3]
        self._create_order(order_type=order_type, pair_name=pair_name)
        if order_type == Order.BUY:
            mock_currency_code = currency_quote_code
            mock_amount = self.order.amount_quote
            withdraw_currency_code = currency_base_code
        elif order_type == Order.SELL:
            mock_currency_code = currency_base_code
            mock_amount = self.order.amount_base
            withdraw_currency_code = currency_quote_code
        card_id = UserCards.objects.filter(
            user=self.order.user, currency=mock_currency_code)[0].card_id
        self._create_mocks(
            currency_code=mock_currency_code,
            amount2=mock_amount,
            card_id=card_id
        )
        txs_data = json.loads(self.import_txs)
        import_txs.return_value = txs_data
        reserve_txs.return_value = json.loads(self.completed)
        prepare_txn.return_value = 'txid123454321'
        execute_txn.return_value = True
        self.import_txs_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        tx_pk = Transaction.objects.last().pk
        address = getattr(self, '{}_address'.format(withdraw_currency_code))
        self._update_withdraw_address(self.order, address)
        self.release_task.apply([tx_pk])
        self.order.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED, pair_name)
