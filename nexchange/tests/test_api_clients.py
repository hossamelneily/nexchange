from django.test import TestCase
from nexchange.api_clients.factory import ApiClientFactory
from core.models import Transaction, Currency
from core.tests.utils import data_provider
from unittest.mock import patch
from core.tests.base import SCRYPT_ROOT
from collections import namedtuple


scrypt_check_tx_params = namedtuple(
    'eth_check_tx_params',
    ['case_name', 'tx_count', 'min_confs', 'expected_return']
)


class ApiClientsTestCase(TestCase):

    fixtures = [
        'currency_crypto.json'
    ]

    def __init__(self, *args, **kwargs):
        super(ApiClientsTestCase, self).__init__(*args, **kwargs)
        self.factory = ApiClientFactory()

    def setUp(self):
        self.BTC = Currency.objects.get(code='BTC')

    @data_provider(lambda: (
        scrypt_check_tx_params(
            case_name='1 Confirmation, not confirmed',
            tx_count=1, min_confs=12,
            expected_return=(False, 1)
        ),
        scrypt_check_tx_params(
            case_name='Min Confirmations, confirmed',
            tx_count=12, min_confs=12,
            expected_return=(True, 12)
        ),
        scrypt_check_tx_params(
            case_name='Min Confirmations 0, not confirmed',
            tx_count=0, min_confs=0,
            expected_return=(False, 0)
        ),
    ))
    @patch(SCRYPT_ROOT + '_get_tx')
    def test_check_tx_scrypt(self, get_tx, **kwargs):
        tx = Transaction(tx_id='123')
        self.BTC.min_confirmations = kwargs['min_confs']
        self.BTC.save()
        api = self.factory.get_api_client(self.BTC.wallet)
        get_tx.return_value = {'confirmations': kwargs['tx_count']}
        res = api.check_tx(tx, self.BTC)
        self.assertEqual(res, kwargs['expected_return'], kwargs['case_name'])
