from django.core.exceptions import ValidationError
import requests_mock
from orders.models import Order
from payments.models import Payment, FailedRequest
from time import time
from datetime import date
from dateutil.relativedelta import relativedelta
from payments.tests.base import BaseCardPmtAPITestCase, BaseSofortAPITestCase
from core.tests.utils import data_provider


class CardPmtAPIClientTestCase(BaseCardPmtAPITestCase):

    def test_validate_cvv(self):
        good_cvv = ['123']
        bad_cvv = ['', '1', '12', '1234', '12b']
        for cvv in good_cvv:
            res = self.pmt_client._validate_cvv(cvv)
            self.assertEqual(res['status'], 1)
        for cvv in bad_cvv:
            res = self.pmt_client._validate_cvv(cvv)
            self.assertEqual(res['status'], 0)

    def test_validate_ccn(self):
        valid_mastercard_ccn = ['5393932585574906', '5483872595838316']
        # starts with different numbers
        valid_maestro_ccn = ['5893961121444923', '5038111133596577']
        wrong_length_ccn = ['539393258557490', '54838725958383161234']
        bad_checksum_mastercard_ccn = ['5393932585574907']
        for cnn in valid_mastercard_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertEqual(res['status'], 1)
        for cnn in valid_maestro_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertEqual(res['status'], 0)
        for cnn in wrong_length_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertEqual(res['status'], 0)
        for cnn in bad_checksum_mastercard_ccn:
            res = self.pmt_client._validate_mastercard_ccn(cnn)
            self.assertEqual(res['status'], 0)

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
            self.assertEqual(res['status'], 1)
        for ccexp in invalid_ccexp:
            res = self.pmt_client._validate_ccexp(ccexp)
            self.assertEqual(res['status'], 0)

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
        profile = self.order.user.profile
        failed_requests_before = len(FailedRequest.objects.all())
        failed_profile_requests_before = profile.failed_requests
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
        failed_requests_after = len(FailedRequest.objects.all())
        failed_profile_requests_after = profile.failed_requests
        self.assertEqual(failed_requests_before + 1, failed_requests_after)
        self.assertEqual(failed_profile_requests_before + 1,
                         failed_profile_requests_after)

    @data_provider(lambda: (
        ('<tr><td>STATUS</td><td>1</td></tr>',),
        ('<tr><td>STATUS</td><td>1</td></tr><tr><td>TRANSACTION_ID</td><td>0'
         '</td></tr>',),
    ))
    @requests_mock.mock()
    def test_paid_unconfirmed_if_partialy_bad_response(self,
                                                       transaction_success,
                                                       mock):
        failed_requests_before = len(FailedRequest.objects.all())
        mock.get(self.pmt_client.url, text=transaction_success)
        self.pmt_client.pay_for_the_order(**self.required_params_dict)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID_UNCONFIRMED)
        payments = Payment.objects.filter(
            reference=self.order.unique_reference,
            amount_cash=self.order.amount_quote,
            currency=self.order.pair.quote
        )
        self.assertEqual(len(payments), 0, transaction_success)
        failed_requests_after = len(FailedRequest.objects.all())
        self.assertEqual(failed_requests_before + 1, failed_requests_after,
                         transaction_success)
        self.order.status = Order.INITIAL
        self.order.save()


class SofortAPIClientTestCase(BaseSofortAPITestCase):

    def test_token_generator(self):
        token = self.api_client._generate_token('123', 'hi')
        expected_token = 'MTIzOmhp'
        self.assertEqual(token, expected_token)

    @requests_mock.mock()
    def test_check_get_transaction_history_response(self, mock):
        transaction_xml = self.create_transaction_xml()
        self.mock_transaction_history(mock, transaction_xml)
        response = self.api_client._get_transaction_history()
        self.assertEqual(response.status_code, 200)

    @data_provider(lambda: (
        (0,),
        (1,),
        (2,),
        (15,),
    ))
    @requests_mock.mock()
    def test_get_transaction_history_as_dict(self, transaction_count, mock):
        transactions = ''
        for i in range(transaction_count):
            transaction_xml = self.create_transaction_xml(
                order_id='{}'.format(i + 1)
            )
            transactions += transaction_xml
        self.mock_transaction_history(mock, transactions)
        response = self.api_client.get_transaction_history()
        self.assertEqual(len(response['transactions']), transaction_count,
                         'transaction count:{}'.format(transaction_count))

    @data_provider(lambda: (
        (401, False),
        (404, False),
        (200, True),
        (415, True),
    ))
    @requests_mock.mock()
    def test_fail_get_transaction_history_as_dict(self, status, empty_response,
                                                  mock):
        provider_params = 'status_code:{} , empty:{}'.format(status,
                                                             empty_response)
        transactions = ''
        if empty_response:
            mock.post(self.api_client.url, text='', status_code=status)
        else:
            self.mock_transaction_history(mock, transactions, status=status)
        response = self.api_client.get_transaction_history()
        self.assertIn(
            'error', response, 'error not found on {}'.format(provider_params)
        )
