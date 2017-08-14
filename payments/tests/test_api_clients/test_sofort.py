import requests_mock

from core.tests.utils import data_provider
from payments.tests.test_api_clients.base import BaseSofortAPITestCase


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
