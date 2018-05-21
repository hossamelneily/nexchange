import json
from decimal import Decimal
from random import randint
from time import time

import requests_mock
from django.conf import settings
from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.task_summary import import_transaction_deposit_crypto_invoke, \
    update_pending_transactions_invoke, \
    import_transaction_deposit_uphold_blockchain_invoke
from core.models import Address, Transaction, Currency, Pair
from core.tests.base import TransactionImportBaseTestCase
from core.tests.base import UPHOLD_ROOT, SCRYPT_ROOT, ETH_ROOT, BITTREX_ROOT, \
    OMNI_ROOT, CRYPTONIGHT_ROOT
from core.tests.base import WalletBaseTestCase
from core.tests.utils import data_provider, get_ok_pay_mock
from orders.models import Order
from orders.task_summary import buy_order_release_by_reference_invoke,\
    exchange_order_release_invoke, \
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
from risk_management.tests.base import RiskManagementBaseTestCase
from risk_management.models import Cover, PNLSheet, PNL
from risk_management.task_summary import order_cover_invoke
from unittest import skip


class OKPayEndToEndTestCase(WalletBaseTestCase):
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_no_address(self, send_email,
                                     send_sms, release_payment,
                                     _get_transaction_history,
                                     calculate_quote_from_base, validate):
        # Purge
        Payment.objects.all().delete()
        release_payment.return_value = 'TX123'
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_success_release(self, send_email, send_sms, release_payment,
                             _get_transaction_history,
                             calculate_quote_from_base, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)

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
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_failure_release_no_address(self, send_email, send_sms,
                                        release_payment,
                                        calculate_quote_from_base,
                                        transaction_history, validate):
        release_payment.return_value = 'TX123'
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_success_release(self, send_email, send_sms,
                             release_payment,
                             calculate_quote_from_base,
                             transaction_history, validate):
        release_payment.return_value = 'TX123'
        calculate_quote_from_base.return_value = None
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

        self.assertEqual(order.status, Order.CANCELED)

    def test_success_release_no_ref(self):
        pass

    def test_failure_release_other_pref(self):
        pass

    def test_failure_release_invalid_currency(self):
        pass

    def test_failure_release_invalid_user(self):
        pass


class SellOrderReleaseTaskTestCase(TransactionImportBaseTestCase,
                                   TickerBaseTestCase):
    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['LTCBTC', 'BTCLTC', 'BTCETH', 'BTCDOGE',
                                     'BTCXVG', 'BTCBCH', 'BTCBDG', 'BTCOMG',
                                     'BTCEOS', 'BTCNANO', 'BTCZEC', 'BTCUSDT',
                                     'BTCXMR']
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
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

    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('orders.utils.send_money')
    def test_do_not_set_sell_order_as_PAID(self, send_money, get_txs, get_rtx):
        # TODO: generalise
        send_money.return_value = True
        get_txs.return_value = json.loads(self.import_txs)
        get_rtx.return_value = json.loads(self.completed)

        self.import_txs_task.apply()
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL)

    def test_okpay_send_money_on_release(self):
        pass

    def test_payeer_send_money_on_release(self):
        pass

    def test_unknown_method_do_not_send_money_on_release(self):
        pass


class BuyOrderReleaseFromViewTestCase(WalletBaseTestCase):
    def setUp(self):
        super(BuyOrderReleaseFromViewTestCase, self).setUp()

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
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_release_if_paid_and_withdraaw_address_set(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, calculate_quote_from_base, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)
        self.assertEquals(0, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_withdraw_address_already_set(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, calculate_quote_from_base, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)
        self.assertEquals(0, release_payment.call_count)

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_no_payment(self, send_email,
                                     send_sms,
                                     release_payment,
                                     _get_transaction_history,
                                     calculate_quote_from_base,
                                     validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        calculate_quote_from_base.return_value = None
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
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_fail_release_withdraaw_address_set_no_payment(
            self, send_email, send_sms, release_payment,
            _get_transaction_history, calculate_quote_from_base, validate):
        # Purge
        release_payment.return_value = 'TX123'
        Payment.objects.all().delete()
        calculate_quote_from_base.return_value = None
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
        self.assertEqual(order.status, Order.CANCELED)
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
        reserve_txn.return_value = {
            "status": "completed",
            "type": "deposit",
            "params": {"progress": 999}
        }
        self.update_confirmation_task.apply()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELED)

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
        self.assertEqual(order.status, Order.CANCELED)


class ExchangeOrderReleaseTaskTestCase(TransactionImportBaseTestCase,
                                       TickerBaseTestCase):

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['ETHLTC', 'BTCETH', 'BTCLTC', 'LTCETH',
                                     'ETHBTC', 'LTCBTC', 'ETHDOGE', 'DOGELTC',
                                     'ETHBCH', 'BCHDOGE', 'ZECBTC', 'BTCZEC',
                                     'BTCUSDT', 'XMRBTC', 'BTCXMR']
        super(ExchangeOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.release_task = exchange_order_release_invoke
        self.release_task_periodic = exchange_order_release_periodic

    @data_provider(
        lambda: (
            ('ETHLTC', Order.BUY, False, 3),
            ('BTCETH', Order.BUY, False, 3),
            ('BTCLTC', Order.BUY, True, 3),
            ('LTCETH', Order.BUY, True, 3),
            ('ETHBTC', Order.BUY, False, 3),
            ('LTCBTC', Order.BUY, True, 3),
            ('ETHDOGE', Order.BUY, True, 3),
            ('DOGELTC', Order.BUY, True, 4),
            ('ETHBCH', Order.BUY, True, 3),
            ('BCHDOGE', Order.BUY, True, 3),
            ('ZECBTC', Order.BUY, True, 3),
            ('BTCZEC', Order.BUY, True, 3),
            ('BTCUSDT', Order.BUY, True, 3),
            ('XMRBTC', Order.BUY, True, 3),
            ('BTCXMR', Order.BUY, True, 3),
        )
    )
    @patch(ETH_ROOT + 'net_listening')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch('accounts.tasks.monitor_wallets.app.send_task')
    @patch(ETH_ROOT + '_get_current_block')
    @patch(ETH_ROOT + 'release_coins')
    @patch(ETH_ROOT + '_get_tx_receipt')
    @patch(ETH_ROOT + '_get_tx')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + 'release_coins')
    @patch(SCRYPT_ROOT + '_get_tx')
    @patch(SCRYPT_ROOT + '_get_txs')
    @patch(OMNI_ROOT + 'release_coins')
    @patch(OMNI_ROOT + '_get_tx')
    @patch(OMNI_ROOT + '_get_txs')
    @patch(CRYPTONIGHT_ROOT + 'release_coins')
    @patch(CRYPTONIGHT_ROOT + '_get_tx')
    @patch(CRYPTONIGHT_ROOT + '_get_txs')
    @patch(CRYPTONIGHT_ROOT + 'get_current_block')
    @patch(CRYPTONIGHT_ROOT + 'get_info')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    def test_release_exchange_order(self, pair_name, order_type,
                                    release_with_periodic, base_curr_code_len,
                                    check_tx_uphold,
                                    get_txs_uphold,
                                    prepare_txn_uphold,
                                    execute_txn_uphold,
                                    cryptonight_info,
                                    get_current_block_cryptonight,
                                    get_txs_cryptonight, get_tx_cryptonight,
                                    release_coins_cryptonight,
                                    get_txs_omni, get_tx_omni,
                                    release_coins_omni,
                                    get_txs_scrypt, get_tx_scrypt,
                                    release_coins_scrypt,
                                    get_txs_eth, get_tx_eth,
                                    get_tx_eth_receipt,
                                    release_coins_eth, get_block_eth,
                                    send_task, scrypt_info, eth_listen):
        scrypt_info.return_value = cryptonight_info.return_value ={}
        eth_listen.return_value = True
        currency_quote_code = pair_name[base_curr_code_len:]
        currency_base_code = pair_name[0:base_curr_code_len]
        if currency_base_code == 'DOGE':
            amount_base = 1001
        else:
            amount_base = 0.5
        self._create_order(order_type=order_type, pair_name=pair_name,
                           amount_base=amount_base)
        mock_currency_code = currency_quote_code
        mock_amount = self.order.amount_quote
        withdraw_currency_code = currency_base_code
        mock_currency = Currency.objects.get(code=mock_currency_code)
        card = self.order.deposit_address.reserve

        block_height = 10
        get_cryptonight_txs_result = \
            self.get_cryptonight_raw_txs(mock_currency, mock_amount,
                                         card.address, block_height)['result']['in']

        if mock_currency.wallet == 'api1':
            card_id = card.card_id
            get_txs_uphold.return_value = [
                self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
            ]
        else:
            get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                          card.address)
            get_txs_scrypt.return_value = self.get_scrypt_tx(mock_amount,
                                                             card.address)
            get_txs_omni.return_value = self.get_omni_tx(mock_amount,
                                                         card.address)
            get_txs_cryptonight.return_value = get_cryptonight_txs_result
        confs = 249
        check_tx_uphold.return_value = True, confs

        get_tx_cryptonight.return_value = get_cryptonight_txs_result[0]
        get_current_block_cryptonight.return_value = {'height': block_height + 11}

        get_tx_omni.return_value = self.get_omni_tx_raw_confirmed(
            self.get_omni_tx_raw_unconfirmed(mock_amount, card.address))
        get_tx_scrypt.return_value = {
            'confirmations': confs
        }
        get_tx_eth.return_value = self.get_ethash_tx_raw(
            self.ETH, Decimal('1'), '0x', block_number=0
        )
        get_tx_eth_receipt.return_value = self.get_ethash_tx_receipt_raw(
            self.ETH, Decimal('1'), status=1
        )
        get_block_eth.return_value = confs
        self.import_txs_task.apply()
        prepare_txn_uphold.return_value = release_coins_scrypt.return_value = \
            release_coins_eth.return_value = release_coins_omni.return_value = \
            release_coins_cryptonight.return_value = \
            'txid_{}{}'.format(time(), randint(1, 999))
        execute_txn_uphold.return_value = {'code': 'OK'}
        self.order.refresh_from_db()

        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)

        self.update_confirmation_task.apply()
        self.assertEqual(2, send_task.call_count, pair_name)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID, pair_name)
        address = getattr(self, '{}_address'.format(withdraw_currency_code))
        self._update_withdraw_address(self.order, address)
        self.order.refresh_from_db()
        self.assertIn(self.order.status, Order.IN_RELEASED, pair_name)
        t1 = self.order.transactions.first()
        t2 = self.order.transactions.last()
        self.assertEqual(t1.type, Transaction.DEPOSIT, pair_name)
        self.assertEqual(t2.type, Transaction.WITHDRAW, pair_name)
        t_quote = t1
        t_base = t2
        self.assertEqual(t_quote.amount, self.order.amount_quote, pair_name)
        self.assertEqual(t_base.amount, self.order.amount_base, pair_name)
        self.assertEqual(t_quote.currency, self.order.pair.quote, pair_name)
        self.assertEqual(t_base.currency, self.order.pair.base, pair_name)

    @data_provider(
        lambda: (
            ('ETHLTC',),
            # ('ETHRNS',),
            ('BTCLTC',),
            ('BTCETH',),
        )
    )
    @patch('orders.models.Order.expired')
    @patch(ETH_ROOT + 'release_coins')
    @patch(ETH_ROOT + '_get_tx')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + 'release_coins')
    @patch(SCRYPT_ROOT + '_get_tx')
    @patch(SCRYPT_ROOT + '_get_txs')
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
                                                 get_txs_eth, get_tx_eth,
                                                 release_coins_eth,
                                                 order_expired):
        order_expired.return_value = True
        currency_quote_code = pair_name[3:]
        self._create_order(pair_name=pair_name)
        mock_currency_code = currency_quote_code
        mock_amount = self.order.amount_quote
        mock_currency = Currency.objects.get(code=mock_currency_code)

        card = self.order.deposit_address.reserve

        if mock_currency.wallet == 'api1':
            card_id = card.card_id
            get_txs_uphold.return_value = [
                self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
            ]
        else:
            get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                          card.address)
            get_txs_scrypt.return_value = self.get_scrypt_tx(mock_amount,
                                                             card.address)
        check_tx_uphold.return_value = True, 999
        get_tx_eth.return_value = get_tx_scrypt.return_value = {
            'confirmations': 249
        }
        self.import_txs_task.apply()
        release_coins_scrypt.return_value = \
            release_coins_eth.return_value = \
            'txid_{}{}'.format(time(), randint(1, 999))

        self.order.refresh_from_db()
        self.assertTrue(self.order.expired)
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED,
                         pair_name)
        self.assertEqual(
            self.order.payment_window, settings.PAYMENT_WINDOW * 2, pair_name)


class SofortEndToEndTestCase(BaseSofortAPITestCase,
                             TransactionImportBaseTestCase,
                             TickerBaseTestCase):

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['LTCBTC', 'BTCLTC', 'BTCETH', 'BTCDOGE',
                                     'BTCXVG', 'BTCBCH', 'BTCBDG', 'BTCOMG',
                                     'BTCEOS', 'BTCNANO', 'BTCZEC', 'BTCUSDT',
                                     'BTCXMR']
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
        self.assertEqual(self.order.status, Order.CANCELED)
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

        p.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.order.status, Order.CANCELED)

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
        self.assertEqual(self.order.status, Order.CANCELED)


class AdvCashE2ETestCase(BaseAdvCashAPIClientTestCase,
                         TransactionImportBaseTestCase, TickerBaseTestCase):
    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['LTCBTC', 'BTCLTC', 'BTCETH', 'BTCDOGE',
                                     'BTCXVG', 'BTCBCH', 'BTCBDG', 'BTCOMG',
                                     'BTCEOS', 'BTCNANO', 'BTCZEC', 'BTCUSDT',
                                     'BTCXMR']
        super(AdvCashE2ETestCase, self).setUp()
        self.payment_importer = run_adv_cash
        self.import_txs_task = import_transaction_deposit_crypto_invoke
        self.update_confirmation_task = update_pending_transactions_invoke
        self.user.email = "Sir@test.alot"
        self.user.save()
        self.completed = '{"status": "completed", "type": "deposit",' \
                         '"params": {"progress": 999}}'

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
        self._create_order(amount_base=0.2, pair_name=pair_name,
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
        self.assertEqual(self.order.status, Order.CANCELED)
        return

    @skip('FIXME: need to make reverse Fiat pairs working')
    @data_provider(lambda: (
        ('EURBTC', 'EURBTC', Order.BUY),
    ))
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient._send_money')
    def test_success_release_FIATCRYPTO(self, name, pair_name, order_type,
                                        send_money, prepare_txn, execute_txn,
                                        get_txs, get_rtx, check_tx_uphold):
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

        card_id = card.card_id
        get_txs.return_value = [
            self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
        ]
        check_tx_uphold.return_value = True, 999
        self.import_txs_task.apply()
        tx_id = 'txid_{}{}'.format(time(), randint(1, 999))
        prepare_txn.return_value = tx_id
        execute_txn.return_value = True
        send_money.return_value = self.mock_advcash_sendmoney_response(
            tx_id=tx_id)

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()

        self.order.refresh_from_db()

        self.assertEqual(self.order.status, Order.COMPLETED, name)

    @skip('FIXME: need to make reverse Fiat pairs working')
    @data_provider(lambda: (
        ('EURBTC', 'EURBTC', Order.BUY),
    ))
    @patch('nexchange.api_clients.uphold.UpholdApiClient.check_tx')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.send_money')
    def test_success_release_FIATCRYPTO_fail(self, name, pair_name, order_type,
                                             send_money, prepare_txn,
                                             execute_txn, get_txs, get_rtx,
                                             check_tx_uphold):
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

        card_id = card.card_id
        get_txs.return_value = [
            self.get_uphold_tx(mock_currency_code, mock_amount, card_id)
        ]
        check_tx_uphold.return_value = True, 999
        self.import_txs_task.apply()
        tx_id = 'txid_{}{}'.format(time(), randint(1, 999))
        prepare_txn.return_value = tx_id
        execute_txn.return_value = True
        send_money.return_value = {'status': 'ERROR'}
        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)
        self.update_confirmation_task.apply()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PRE_RELEASE, name)
        self.assertTrue(self.order.flagged, name)


class BlockchainImporterTaskTestCase(TickerBaseTestCase):

    def setUp(self):
        super(BlockchainImporterTaskTestCase, self).setUp()
        self.import_txs_task = \
            import_transaction_deposit_uphold_blockchain_invoke
        old_orders = Order.objects.all()
        for order in old_orders:
            order.cancel()

    def mock_order_blockchain_tx_import(self, order, mock):
        currency = order.pair.quote.code
        if currency in ['BTC', 'LTC', 'ETH']:
            url = 'https://api.blockcypher.com/v1/{}/main/addrs/{}'.format(
                currency.lower(),
                order.deposit_address.address)
            times_satoshi = 1e18 if currency == 'ETH' else 1e8
            response = \
                '{{"txrefs":[{{"tx_input_n": -1, "tx_hash": "{}", ' \
                '"value": {}}}]}}'.format(
                    self.generate_txn_id(),
                    int(order.amount_quote * Decimal(times_satoshi))
                )
            mock.get(url, text=response)
        if currency in ['BCH']:
            url = 'https://bitcoincash.blockexplorer.com/api/addr/{}/utxo'.\
                format(order.deposit_address.address)
            response = \
                '[{{"txid": "{}", "amount": {}}}]'.format(
                    self.generate_txn_id(),
                    order.amount_quote
                )
            mock.get(url, text=response)

    @skip('Do not import tx with blockchain/ Uphold doesnt work anymore')
    @data_provider(
        lambda: (('ETHLTC',), ('BTCETH',), ('BCHBTC',), ('LTCBCH',),)
    )
    @requests_mock.mock()
    def test_import_tx_with_blockchain(self, pair_name, mock):
        amount_base = 0.5
        self._create_order(pair_name=pair_name, amount_base=amount_base)

        self.mock_order_blockchain_tx_import(self.order, mock)
        self.import_txs_task()

        self.order.refresh_from_db()
        self.assertEquals(self.order.status, Order.PAID_UNCONFIRMED, pair_name)


class OrderCoverTaskTestCase(TransactionImportBaseTestCase,
                             TickerBaseTestCase, RiskManagementBaseTestCase):

    fixtures = [
        'market.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'currency_tokens.json',
        'pairs_cross.json',
        'pairs_btc.json',
        'payment_method.json',
        'payment_preference.json',
        'reserve.json',
        'account.json'
    ]

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['XVGBTC', 'BTCXVG', 'LTCXVG', 'XVGETH',
                                     'ETHXVG']
        super(OrderCoverTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_crypto_invoke

    @data_provider(
        lambda: (
            ('XVGBTC', 4000, 'amount_base'),
            ('BTCXVG', 0.02, 'amount_quote'),
            ('LTCXVG', 0.2, 'amount_quote'),
            ('XVGETH', 3000, 'amount_base'),
        )
    )
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'get_main_address')
    @patch(BITTREX_ROOT + 'release_coins')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + '_get_txs')
    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch(SCRYPT_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_create_xvg_cover(self, pair_name, amount_base, trade_amount_key,
                              _get_balance, get_balance_scrypt, get_ticker,
                              buy_limit, sell_limit, withdraw,
                              get_txs_scrypt, get_txs_eth, release_coins,
                              get_main_address, scrypt_info):
        scrypt_info.return_value = {}
        get_main_address.return_value = verge_address = 'VERGEaddress'
        ask = bid = Decimal('0.0012')
        pair_trade = Pair.objects.get(name='XVGBTC')
        xvg = pair_trade.base
        xvg.execute_cover = True
        xvg.save()
        withdraw_tx_id = '123'
        buy_tx_id = self.generate_txn_id()
        sell_tx_id = self.generate_txn_id()
        self._create_order(pair_name=pair_name, amount_base=amount_base)
        mock_amount = self.order.amount_quote
        xvg_amount = getattr(self.order, trade_amount_key)
        balance_bittrex = xvg_amount
        balance_main = xvg_amount / Decimal('2')

        # Import mocks
        card = self.order.deposit_address.reserve
        get_txs_scrypt.return_value = self.get_scrypt_tx(
            mock_amount, card.address
        )
        get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                      card.address)
        # Trade mocks
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        withdraw.return_value = {'result': {'uuid': withdraw_tx_id}}
        buy_limit.return_value = {'result': {'uuid': buy_tx_id}}
        sell_limit.return_value = {'result': {'uuid': sell_tx_id}}
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask, bid=bid)

        self.import_txs_task.apply()

        cover = Cover.objects.latest('id')
        cover_order = cover.orders.last()
        self.assertEqual(self.order, cover_order, pair_name)
        self.assertEqual(cover.rate, ask, pair_name)
        self.assertEqual(cover.amount_base, xvg_amount, pair_name)
        self.assertEqual(cover.pair, pair_trade, pair_name)
        self.assertAlmostEqual(cover.amount_quote, ask * cover.amount_base, 7,
                               pair_name)
        if self.order.pair.base.code == 'XVG':
            expected_type = cover.BUY
            expected_id = buy_tx_id
        elif self.order.pair.quote.code == 'XVG':
            expected_type = cover.SELL
            expected_id = sell_tx_id
        self.assertEqual(cover.cover_type, expected_type, pair_name)
        self.assertEqual(cover.cover_id, expected_id, pair_name)
        self.assertIn(self.order, cover.orders.all())
        # Cover order Again
        order_cover_invoke.apply([self.order.pk])
        new_cover = Cover.objects.latest('id')
        self.assertEqual(cover, new_cover)
        # Check cover sent
        if expected_type == cover.BUY:
            release_coins.assert_called_once()
            main_account = cover.account.reserve.account_set.get(
                is_main_account=True)
            release_coins.assert_called_with(
                pair_trade.base, verge_address,
                balance_bittrex - balance_main + main_account.minimal_reserve
            )
        else:
            release_coins.assert_not_called()

    @patch(BITTREX_ROOT + 'release_coins')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + '_get_txs')
    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch(SCRYPT_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_pnl_of_cover_buy(self, _get_balance, get_balance_scrypt,
                              get_ticker, buy_limit, sell_limit, withdraw,
                              get_txs_scrypt, get_txs_eth, release_coins):
        for order in Order.objects.filter(status=Order.COMPLETED):
            order.status = Order.CANCELED
            with patch('orders.models.Order._validate_status'):
                order.save()
        ask = bid = Decimal('0.0012')
        pair_trade = Pair.objects.get(name='XVGBTC')
        xvg = pair_trade.base
        xvg.execute_cover = True
        xvg.save()
        withdraw_tx_id = '123'
        buy_tx_id = self.generate_txn_id()
        sell_tx_id = self.generate_txn_id()
        self._create_order(pair_name='XVGETH', amount_base=3000)
        order = self.order
        mock_amount = self.order.amount_quote
        xvg_amount = self.order.amount_base
        balance_bittrex = xvg_amount
        balance_main = xvg_amount / Decimal('2')

        # Import mocks
        card = self.order.deposit_address.reserve
        get_txs_scrypt.return_value = self.get_scrypt_tx(
            mock_amount, card.address
        )
        get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                      card.address)
        # Trade mocks
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        withdraw.return_value = {'result': {'uuid': withdraw_tx_id}}
        buy_limit.return_value = {'result': {'uuid': buy_tx_id}}
        sell_limit.return_value = {'result': {'uuid': sell_tx_id}}
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask, bid=bid)

        self.import_txs_task.apply()

        cover = Cover.objects.latest('id')
        order.status = Order.COMPLETED
        order.save()
        order.refresh_from_db()
        self.assertEqual(cover.status, cover.EXECUTED)
        sheet = PNLSheet()
        sheet.save()
        expected_positions = {
            'BTC': - cover.amount_quote,
            'ETH': order.amount_quote
        }
        for key, value in sheet.positions.items():
            expected_value = expected_positions.get(key, Decimal('0'))
            self.assertEqual(
                expected_value, value, 'Bad {} position'.format(key)
            )
        order_pnl = sheet.pnl_set.get(pair__name='ETHXVG')
        self.assertEqual(order_pnl.position, -order.amount_base)
        self.assertEqual(order_pnl.base_position, order.amount_quote)
        case = 'Cover.pair - opposite, cover type - BUY'
        cover_pnl = sheet.pnl_set.get(pair__name='BTCXVG')
        self.assertEqual(cover_pnl.position, cover.amount_base, case)
        self.assertEqual(cover_pnl.base_position, -cover.amount_quote, case)
        xvgbtc_pnl = PNL(pair=pair_trade)
        xvgbtc_pnl.save()
        case = 'Cover.pair - pnl.pair, cover type - BUY'
        self.assertEqual(xvgbtc_pnl.pair.name, 'XVGBTC')
        self.assertEqual(xvgbtc_pnl.position, -cover.amount_quote, case)
        self.assertEqual(xvgbtc_pnl.base_position, cover.amount_base, case)

    @patch(BITTREX_ROOT + 'release_coins')
    @patch(ETH_ROOT + '_get_txs')
    @patch(SCRYPT_ROOT + '_get_txs')
    @patch('nexchange.api_clients.bittrex.Bittrex.withdraw')
    @patch('nexchange.api_clients.bittrex.Bittrex.sell_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.buy_limit')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_ticker')
    @patch(SCRYPT_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_pnl_of_cover_sell(self, _get_balance, get_balance_scrypt,
                               get_ticker, buy_limit, sell_limit, withdraw,
                               get_txs_scrypt, get_txs_eth, release_coins):
        for order in Order.objects.filter(status=Order.COMPLETED):
            order.status = Order.CANCELED
            with patch('orders.models.Order._validate_status'):
                order.save()
        ask = bid = Decimal('0.000012')
        pair_trade = Pair.objects.get(name='XVGBTC')
        xvg = pair_trade.base
        xvg.execute_cover = True
        xvg.save()
        withdraw_tx_id = '123'
        buy_tx_id = self.generate_txn_id()
        sell_tx_id = self.generate_txn_id()
        self._create_order(pair_name='ETHXVG', amount_base=3000)
        order = self.order
        mock_amount = self.order.amount_quote
        xvg_amount = self.order.amount_base
        balance_bittrex = xvg_amount
        balance_main = xvg_amount / Decimal('2')

        # Import mocks
        card = self.order.deposit_address.reserve
        get_txs_scrypt.return_value = self.get_scrypt_tx(
            mock_amount, card.address
        )
        get_txs_eth.return_value = self.get_ethash_tx(mock_amount,
                                                      card.address)
        # Trade mocks
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        withdraw.return_value = {'result': {'uuid': withdraw_tx_id}}
        buy_limit.return_value = {'result': {'uuid': buy_tx_id}}
        sell_limit.return_value = {'result': {'uuid': sell_tx_id}}
        get_ticker.return_value = self._get_bittrex_get_ticker_response(
            ask=ask, bid=bid)

        self.import_txs_task.apply()

        cover = Cover.objects.latest('id')
        order.status = Order.COMPLETED
        order.save()
        order.refresh_from_db()
        self.assertEqual(cover.status, cover.EXECUTED)
        sheet = PNLSheet()
        sheet.save()
        expected_positions = {
            'BTC': cover.amount_quote,
            'ETH': - order.amount_base
        }
        for key, value in sheet.positions.items():
            expected_value = expected_positions.get(key, Decimal('0'))
            self.assertEqual(
                expected_value, value, 'Bad {} position'.format(key)
            )
        order_pnl = sheet.pnl_set.get(pair__name='ETHXVG')
        self.assertEqual(order_pnl.position, order.amount_quote)
        self.assertEqual(order_pnl.base_position, -order.amount_base)
        case = 'Cover.pair - opposite, cover type - SELL'
        cover_pnl = sheet.pnl_set.get(pair__name='BTCXVG')
        self.assertEqual(cover_pnl.position, - cover.amount_base, case)
        self.assertEqual(cover_pnl.base_position, cover.amount_quote, case)
        xvgbtc_pnl = PNL(pair=pair_trade)
        xvgbtc_pnl.save()
        case = 'Cover.pair - pnl.pair, cover type - SELL'
        self.assertEqual(xvgbtc_pnl.pair.name, 'XVGBTC', case)
        self.assertEqual(xvgbtc_pnl.position, cover.amount_quote, case)
        self.assertEqual(xvgbtc_pnl.base_position, - cover.amount_base, case)
