from payments.tests.base import BaseSofortAPITestCase
from orders.models import Order
from payments.models import Payment
from payments.tasks.generic.sofort import SofortPaymentChecker
import requests_mock
from core.tests.utils import data_provider
from copy import deepcopy


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
