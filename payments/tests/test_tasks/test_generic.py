from copy import deepcopy
from unittest.mock import patch
from decimal import Decimal

import requests_mock

from core.tests.utils import data_provider
from orders.models import Order
from payments.models import Payment
from payments.tasks.generic.sofort import SofortPaymentChecker
from payments.tasks.generic.adv_cash import AdvCashPaymentChecker
from payments.tests.test_api_clients.base import BaseSofortAPITestCase
from payments.tests.test_api_clients.test_adv_cash import \
    BaseAdvCashAPIClientTestCase
from payments.task_summary import run_adv_cash


class SofortGenericTaskTestCase(BaseSofortAPITestCase):

    def setUp(self):
        super(SofortGenericTaskTestCase, self).setUp()
        self.payments_checker = SofortPaymentChecker()
        self.sender_name = 'Sender Awesome'
        self.iban = 'DE86000000002345678902'
        self.transaction_data = {
            'order_id': self.order.unique_reference,
            'amount': self.order.amount_quote,
            'currency': self.order.pair.quote.code,
            'sender_name': self.sender_name,
            'iban': self.iban
        }

    @requests_mock.mock()
    def test_order_paid_after_transaction_import(self, mock):
        transaction_xml = self.create_transaction_xml(
            **self.transaction_data
        )
        self.mock_transaction_history(mock, transaction_xml)
        self.payments_checker.run()

        p = Payment.objects.filter(
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote,
            reference=self.order.unique_reference
        )
        self.assertEqual(1, len(p))
        pref = p[0].payment_preference
        self.assertEqual(self.sender_name, pref.identifier)
        self.assertEqual(self.iban, pref.secondary_identifier)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)

    @data_provider(lambda: (
        ('currency', 'USD'),
        ('order_id', 'bad_id'),
        ('amount', '0.00001'),
    ))
    @requests_mock.mock()
    def test_order_paid_failed(self, key, value, mock):
        transaction_data = deepcopy(self.transaction_data)
        transaction_data.update({key: value})
        transaction_xml = self.create_transaction_xml(
            **transaction_data
        )
        self.mock_transaction_history(mock, transaction_xml)
        self.payments_checker.run()

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL)


class AdvCashGenericTaskTestCase(BaseAdvCashAPIClientTestCase):

    def setUp(self):
        super(AdvCashGenericTaskTestCase, self).setUp()
        self.importer = AdvCashPaymentChecker()

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_get_transactions(self, history_patch):
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response()
        res = self.importer.get_transactions()
        self.assertEqual(1, len(res))
        self.check_history_transactions_keys(res)

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_iterate_only_incoming(self, history_patch):
        txs_incoming = self.mock_advcash_transaction_response(
            direction='INCOMING')
        txs_outgoing = self.mock_advcash_transaction_response(
            direction='OUTGOING')
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(
                transactions=txs_incoming + txs_outgoing)
        self.importer.transactions = self.importer.get_transactions()
        self.assertEqual(2, len(self.importer.transactions))
        count = 0
        for trans in self.importer.transactions_iterator():
            count += 1
            self.importer.parse_data(trans)
            data_keys = self.importer.data.keys()
            expected_keys = \
                self.importer.required_data_keys \
                + self.importer.essential_data_keys \
                + self.importer.transaction_data_keys
            for key in expected_keys:
                self.assertIn(key, data_keys)
        self.assertEqual(1, count)

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_order_paid_with_adv_cash(self, history_patch):
        txn = self.mock_advcash_transaction_response(**self.payment_data)
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(transactions=txn)
        self.importer.run()
        p = Payment.objects.filter(
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote,
            reference=self.order.unique_reference
        )
        self.assertEqual(1, len(p))
        pref = p[0].payment_preference
        self.assertEqual(self.sender_email, pref.identifier)
        self.assertEqual(self.sender_wallet, pref.secondary_identifier)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_order_paid_with_adv_cash_only_comment(self, history_patch):
        self.payment_data.update({'unique_ref': None})
        self.payment_data.update(
            {'amount': self.order.amount_quote + Decimal('1.0')})
        txn = self.mock_advcash_transaction_response(**self.payment_data)
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(transactions=txn)
        self.importer.run()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_order_not_paid_with_adv_cash_no_ref_bad_comment(self,
                                                             history_patch):
        self.payment_data.update({'unique_ref': None,
                                  'comment': 'bad comment'})
        self.payment_data.update(
            {'amount': self.order.amount_quote + Decimal('1.0')})
        txn = self.mock_advcash_transaction_response(**self.payment_data)
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(transactions=txn)
        self.importer.run()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL)

    @data_provider(lambda: (
        ('wrong currency', {'currency': 'USD'}),
        ('wrong reference', {'unique_ref': 'bad_id', 'comment': 'bad_id',
                             'amount': '501.00'}),
        ('wrong amount', {'amount': '0.00001'}),
    ))
    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_order_paid_failed(self, name, update_data, history_patch):
        payment_data = deepcopy(self.payment_data)
        payment_data.update(update_data)
        txn = self.mock_advcash_transaction_response(**payment_data)
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(transactions=txn)
        self.importer.run()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL, name)

    @patch('payments.tasks.generic.adv_cash.AdvCashPaymentChecker.run')
    def test_run_adv_cash_task(self, run_patch):
        run_adv_cash.apply()
        self.assertEqual(1, run_patch.call_count)
