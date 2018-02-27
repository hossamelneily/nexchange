from django.test import TestCase
from nexchange.api_clients.factory import ApiClientFactory
from core.models import Transaction, Currency
from core.tests.utils import data_provider
from unittest.mock import patch
from core.tests.base import ETH_ROOT, SCRYPT_ROOT
from collections import namedtuple

ethash_check_tx_params = namedtuple(
    'eth_check_tx_params',
    ['case_name', 'tx_block', 'current_block', 'tx_status', 'min_confs',
     'expected_return']
)
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
        self.ETH = Currency.objects.get(code='ETH')
        self.BTC = Currency.objects.get(code='BTC')

    @data_provider(lambda: (
        ethash_check_tx_params(
            case_name='Min Confirmation, confirmed',
            tx_block=0, current_block=12, tx_status=1, min_confs=12,
            expected_return=(True, 12)
        ),
        ethash_check_tx_params(
            case_name='1 Confirmation, not confirmed',
            tx_block=0, current_block=1, tx_status=1, min_confs=12,
            expected_return=(False, 1)
        ),
        ethash_check_tx_params(
            case_name='Min confirmations 0, not confirmed',
            tx_block=0, current_block=0, tx_status=1, min_confs=0,
            expected_return=(False, 0)
        ),
        ethash_check_tx_params(
            case_name='Min confirmations with bad status, not confirmed',
            tx_block=0, current_block=12, tx_status=0, min_confs=12,
            expected_return=(False, 0)
        ),
    ))
    @patch(ETH_ROOT + '_get_current_block')
    @patch(ETH_ROOT + '_get_tx_receipt')
    @patch(ETH_ROOT + '_get_tx')
    def test_check_tx_ethash(self, get_tx, get_tx_receipt, get_current_block,
                             **kwargs):
        tx_id = '123'
        self.ETH.min_confirmations = kwargs['min_confs']
        self.ETH.save()
        api = self.factory.get_api_client(self.ETH.wallet)
        get_tx.return_value = {'blockNumber': kwargs['tx_block']}
        get_tx_receipt.return_value = {'status': kwargs['tx_status']}
        get_current_block.return_value = kwargs['current_block']
        res = api.check_tx(tx_id, self.ETH)
        self.assertEqual(res, kwargs['expected_return'], kwargs['case_name'])

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
