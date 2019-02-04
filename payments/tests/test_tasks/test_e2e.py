from unittest.mock import patch

from django.conf import settings
from payments.tasks.generic.payeer import PayeerPaymentChecker

from core.tests.base import WalletBaseTestCase
from orders.models import Order
from payments.models import Payment, PaymentPreference
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from core.tests.utils import get_ok_pay_mock
from ..base import BaseFiatOrderTestCase
import requests_mock
import json
from risk_management import task_summary as risk_tasks
from decimal import Decimal
from ticker.models import Price, Ticker
from core.models import Pair


class WalletAPITestCase(WalletBaseTestCase):
    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    def test_confirm_order_payment_with_okpay_celery(self,
                                                     history,
                                                     convert_to_cash,
                                                     validate):
        history.return_value = get_ok_pay_mock()
        convert_to_cash.return_value = None
        validate.return_value = True
        order = Order(**self.okpay_order_data)
        order.save()
        import_okpay_payments = OkPayPaymentChecker()
        import_okpay_payments.run()

        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
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
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        order.refresh_from_db()
        # check that pref is intact
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))
        self.assertEqual(pref[0].identifier, 'dobbscoin@gmail.com')
        self.assertEqual(pref[0].secondary_identifier, 'OK487565544')
        # self.assertIn(order.status, Order.IN_PAID)
        # FIXME: CANCEL because fiat needs refactoring
        self.assertEqual(order.status, Order.CANCELED)

    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.calculate_quote_from_base')
    def test_import_payeer_invalid_wallet(self,
                                          convert_to_cash, trans_hist):
        convert_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        trans_hist.return_value = {
            '1': {
                'id': '1',
                'type': 'transfer',
                'status': 'success',
                'creditedCurrency': self.EUR.code,
                'creditedAmount': str(self.payeer_order_data['amount_quote']),
                'to': 'tata',
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.payeer_order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )
        self.assertEqual(0, len(p))
        # assert payment pref is created correctly

    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.calculate_quote_from_base')
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
                'creditedAmount': str(self.payeer_order_data['amount_quote']),
                'to': 'tata',
                'shopOrderId': self.payeer_order_data['unique_reference'],
                'comment': self.payeer_order_data['unique_reference'],
                'from': sender
            }
        }
        order = Order(**self.payeer_order_data)
        order.save()
        import_payeer_payments = PayeerPaymentChecker()
        import_payeer_payments.run()
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )
        self.assertEqual(0, len(p))
        # assert payment pref is created correctly

    @patch('payments.tasks.generic.base.BasePaymentChecker'
           '.validate_beneficiary')
    @patch('payments.api_clients.payeer.PayeerAPIClient.'
           'get_transaction_history')
    @patch('orders.models.Order.calculate_quote_from_base')
    def test_confirm_order_payment_with_payeer_celery(self, convert_to_cash,
                                                      trans_hist, validate):
        convert_to_cash.return_value = None
        sender = 'zaza'
        # TODO: get fixutre
        trans_hist.return_value = {
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
        p = Payment.objects.filter(
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
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
            amount_cash=order.amount_quote,
            currency=order.pair.quote,
            reference=order.unique_reference
        )
        self.assertEqual(1, len(p))
        pref = PaymentPreference.objects.filter(payment=p[0])
        self.assertEqual(1, len(pref))

        self.assertEquals(pref[0].identifier,
                          sender)


class FiatCoverTestCase(BaseFiatOrderTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLE_FIAT = ['USD', 'EUR']
        cls.ENABLED_TICKER_PAIRS = ['DOGEBTC', 'BTCDOGE']
        super(FiatCoverTestCase, cls).setUpClass()

    def _create_price(self, pair_name, rate):
        pair = Pair.objects.get(name=pair_name)
        ticker = Ticker.objects.create(pair=pair, ask=rate, bid=rate)
        Price.objects.create(pair=pair, ticker=ticker)
        reverse_pair = pair.reverse_pair
        if reverse_pair:
            reverse_rate = Decimal('1') / rate
            ticker = Ticker.objects.create(
                pair=reverse_pair, ask=reverse_rate, bid=reverse_rate
            )
            Price.objects.create(pair=reverse_pair, ticker=ticker)

    def _create_simple_rates(self):
        self._create_price('DOGEBTC', Decimal('1e-6'))
        self._create_price('BTCUSD', Decimal('3750'))
        self._create_price('BTCEUR', Decimal('3000'))
        self._create_price('DOGEEUR', Decimal('0.003'))
        self._create_price('DOGEUSD', Decimal('0.00375'))

    @requests_mock.mock()
    @patch('nexchange.api_clients.kraken.krakenex.API.query_public')
    @patch('nexchange.api_clients.kraken.krakenex.API.query_private')
    @patch('payments.api_clients.safe_charge.app.send_task')
    @patch('orders.models.Order._validate_status')
    def test_cover_fiat_order(self, mock, _validate_status, send_task,
                              kraken_private, kraken_public):
        trade_id = self.generate_txn_id()
        self._create_simple_rates()
        btceur_rate = \
            Price.objects.filter(pair__name='BTCEUR').latest('id').ticker.rate
        # kraken current rate is higher therefore calculated rate is selected
        kraken_rate = Decimal('1.1') * btceur_rate
        kraken_public.return_value = {
            'error': [],
            'result': {'XXBTZEUR': {'a': [kraken_rate], 'b': [kraken_rate]}}
        }
        kraken_private.return_value = {
            'error': [],
            'result': {
                'descr': {'order': 'buy 0.00250000 XBTEUR @ limit 3108.0'},
                'txid': [trade_id]
            }
        }
        order = self._create_order_api(
            pair_name='DOGEUSD', address='DPjMRpkNKEfnYVHqmAan4FbriqP4DyUt2u'
        )
        btcusd = order.pair
        btcusd.fee_ask = Decimal('0')
        btcusd.fee_bid = Decimal('0')
        btcusd.save()
        usd = order.pair.quote
        usd.execute_cover = True
        usd.save()
        url = self.payment_handler.api.url
        dynamic_resp = payment_resp = {
            'status': 'SUCCESS',
            'transactionStatus': 'APPROVED',
            'orderId': '12345',
            'transactionId': '54321'
        }
        token_resp = {'sessionToken': 'token_awesome', 'status': 'SUCCESS'}
        mock.post(url.format('api/v1/dynamic3D'),
                  text=json.dumps(dynamic_resp))
        mock.post(url.format('api/v1/payment3D'),
                  text=json.dumps(payment_resp))
        mock.post(url.format('api/v1/getSessionToken'),
                  text=json.dumps(token_resp))
        _validate_status.return_value = True
        client_request_id = order.unique_reference
        session_token = self.payment_handler.api.getSessionToken(
            **{'clientRequestId': client_request_id}
        )['sessionToken']
        params = {
            'sessionToken': session_token,
            'clientRequestId': client_request_id,
            'cardData': {
                'cardNumber': '375510513169537',
                'cardHolderName': 'Sir Testalot',
                'expirationMonth': '01',
                'expirationYear': '22',
                'CVV': '123'
            }
        }
        # Register Payment
        self.payment_handler.register_payment(order.pk, **params)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID_UNCONFIRMED)
        payment = order.payment_set.last()
        self.assertEqual(order.amount_quote, payment.amount_cash)
        self.assertEqual(dynamic_resp['orderId'], payment.payment_system_id)
        self.assertEqual(dynamic_resp['transactionId'],
                         payment.secondary_payment_system_id)
        self.assertEqual(Payment.DEPOSIT, payment.type)
        self.assertEqual(order.pair.quote, payment.currency)
        pref = payment.payment_preference
        card_data = params['cardData']
        self.assertEqual(card_data['cardNumber'], pref.identifier)
        self.assertEqual(card_data['cardHolderName'],
                         pref.secondary_identifier)
        self.assertEqual(
            '{}/{}'.format(
                card_data['expirationMonth'],
                card_data['expirationYear'],
            ),
            pref.ccexp
        )
        self.assertEqual(card_data['CVV'], pref.cvv)

        # Confirm Payment
        self.payment_handler.confirm_payment(payment.pk, **params)

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        self.assertTrue(payment.is_complete)
        self.assertTrue(payment.is_success)
        self.assertFalse(payment.is_redeemed)
        task, task_args = send_task.call_args[0]
        self.assertEqual(task_args[0], order.pk)
        getattr(
            risk_tasks,
            task.split('risk_management.task_summary.')[1]
        ).apply_async(task_args)
        order.refresh_from_db()
        cover = order.covers.get()
        self.assertEqual(cover.status, cover.EXECUTED)
        self.assertEqual(cover.pair.name, 'BTCEUR')
        self.assertEqual(cover.cover_type, cover.BUY)
        cover_quote_in_usd = Price.convert_amount(
            cover.amount_quote, cover.pair.quote, order.pair.quote
        )
        self.assertEqual(cover_quote_in_usd, order.amount_quote_minus_fees, 7)
        cover_quote_in_doge = Price.convert_amount(
            cover.amount_base, cover.pair.base, order.pair.base
        )
        # few DOGE off because doge ticker is near the decimal numbers limit
        self.assertAlmostEqual(cover_quote_in_doge, order.amount_base, 1)
        self.assertEqual(cover.cover_id, trade_id)
