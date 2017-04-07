from django.core.exceptions import ValidationError
import requests_mock
from orders.models import Order
from payments.models import Payment
from time import time
from datetime import date
from dateutil.relativedelta import relativedelta
from payments.tests.base import BaseCardPmtAPITestCase
from core.tests.utils import data_provider


class CardPmtAPIClientTestCase(BaseCardPmtAPITestCase):

    def test_validate_cvv(self):
        good_cvv = ['123']
        bad_cvv = ['', '1', '12', '1234', '12b']
        for cvv in good_cvv:
            res = self.pmt_client._validate_cvv(cvv)
            self.assertTrue(res)
        for cvv in bad_cvv:
            res = self.pmt_client._validate_cvv(cvv)
            self.assertFalse(res)

    def test_validate_ccn(self):
        valid_mastercard_ccn = ['5393932585574906', '5483872595838316']
        # starts with different numbers
        valid_maestro_ccn = ['5893961121444923', '5038111133596577']
        wrong_length_ccn = ['539393258557490', '54838725958383161234']
        bad_checksum_mastercard_ccn = ['5393932585574907']
        for cnn in valid_mastercard_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertTrue(res, cnn)
        for cnn in valid_maestro_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertFalse(res, cnn)
        for cnn in wrong_length_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertFalse(res, cnn)
        for cnn in bad_checksum_mastercard_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertFalse(res, cnn)

    def test_calidate_ccexp(self):
        invalid_format = ['022020', '118']
        now = date.today().strftime('%m%y')
        plus_six_months = (date.today() + relativedelta(months=+6)).strftime(
            '%m%y'
        )
        minus_six_months = (date.today() + relativedelta(months=-6)).strftime(
            '%m%y'
        )
        plus_two_years = (date.today() + relativedelta(years=2)).strftime(
            '%m%y'
        )
        minus_two_years = (date.today() + relativedelta(years=-2)).strftime(
            '%m%y'
        )
        valid_ccexp = [plus_six_months, plus_two_years]
        invalid_ccexp = invalid_format + [now, minus_six_months,
                                          minus_two_years]
        for ccexp in valid_ccexp:
            res = self.pmt_client._validate_ccexp(ccexp)
            self.assertTrue(res, ccexp)
        for ccexp in invalid_ccexp:
            res = self.pmt_client._validate_ccexp(ccexp)
            self.assertFalse(res, ccexp)

    def test_validate_created_url(self):
        url = self.pmt_client._create_tx_url(**self.required_params_dict)
        try:
            self.url_validator(url)
        except ValidationError as e:
            raise ValidationError('{} is not valid. error:{}'.format(url, e))

    def test_read_parameter(self):
        parameter = 'Table parameter'
        expected_value = 'this parameter value'
        cont = '<tr><td>{parameter}</td><td>{expected_value}</td></tr>'.format(
            parameter=parameter,
            expected_value='this parameter value'
        )
        value = self.pmt_client._read_content_table_parameter(cont, parameter)
        self.assertTrue(value, expected_value)
        value = self.pmt_client._read_content_table_parameter(cont, 'nonsense')
        self.assertIsNone(value)

    @requests_mock.mock()
    def test_create_transaction_success(self, mock):
        response_code = '100'
        status = '1'
        transaction_id = '12345'
        transaction_success = self.transaction_response_empty.format(
            response_code=response_code,
            status=status,
            transaction_id=transaction_id
        )
        mock.get(self.pmt_client.url, text=transaction_success)
        response = self.pmt_client.create_transaction(
            **self.required_params_dict
        )
        self.assertEqual(response['response_code'], response_code)
        self.assertEqual(response['status'], status)
        self.assertEqual(response['transaction_id'], transaction_id)

    @requests_mock.mock()
    def test_pay_for_the_order(self, mock):
        response_code = '100'
        status = '1'
        transaction_id = 'tx_id' + str(time())
        transaction_success = self.transaction_response_empty.format(
            response_code=response_code,
            status=status,
            transaction_id=transaction_id
        )
        mock.get(self.pmt_client.url, text=transaction_success)
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)
        payments = Payment.objects.filter(
            reference=self.order.unique_reference,
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote
        )
        self.assertEqual(len(payments), 1)
        pref = payments[0].payment_preference
        location = pref.location
        self.assertIsNotNone(location)
        self.check_location(location, **self.required_params_dict)

    @requests_mock.mock()
    def test_do_not_pay_order_if_transaction_id_is_the_same(self, mock):
        order_2 = Order.objects.create(**self.order_data)
        response_code = '100'
        status = '1'
        transaction_id = '12345'
        transaction_success = self.transaction_response_empty.format(
            response_code=response_code,
            status=status,
            transaction_id=transaction_id
        )
        mock.get(self.pmt_client.url, text=transaction_success)
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)
        self.required_params_dict['orderid'] = order_2.unique_reference
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        order_2.refresh_from_db()
        self.assertEqual(order_2.status, Order.PAID_UNCONFIRMED)

    @requests_mock.mock()
    def test_do_not_pay_for_the_order_bad_pmt_status(self, mock):
        response_code = '100'
        status = '0'
        transaction_id = 'tx_id' + str(time())
        transaction_success = self.transaction_response_empty.format(
            response_code=response_code,
            status=status,
            transaction_id=transaction_id
        )
        mock.get(self.pmt_client.url, text=transaction_success)
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL)
        payments = Payment.objects.filter(
            reference=self.order.unique_reference,
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote
        )
        self.assertEqual(len(payments), 0)

    @data_provider(lambda: (
        ('<tr><td>STATUS</td><td>1</td></tr>',),
        ('<tr><td>STATUS</td><td>1</td></tr><tr><td>TRANSACTION_ID</td><td>0'
         '</td></tr>',),
    ))
    @requests_mock.mock()
    def test_paid_unconfirmed_if_partialy_bad_response(self,
                                                       transaction_success,
                                                       mock):
        mock.get(self.pmt_client.url, text=transaction_success)
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED)
        payments = Payment.objects.filter(
            reference=self.order.unique_reference,
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote
        )
        self.assertEqual(len(payments), 0)
