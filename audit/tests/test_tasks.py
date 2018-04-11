from django.test import TestCase
from audit.task_summary import check_suspicious_transactions_invoke,\
    check_suspicious_transactions_all_currencies_invoke
from audit.models import SuspiciousTransactions
import requests_mock
from unittest.mock import patch
from core.tests.base import ETH_ROOT, SCRYPT_ROOT
import os
from decimal import Decimal
from core.models import Currency


RPC7_PUBLIC_KEY_C1 = '0xmaincard11111111111111111111111111111111'


class AuditBaseTestCase(TestCase):

    fixtures = [
        'currency_crypto.json',
        'currency_tokens.json',
        'pairs_cross.json'
    ]


class AuditTaksTestCase(AuditBaseTestCase):

    def setUp(self):
        super(AuditTaksTestCase, self).setUp()
        self.checker = check_suspicious_transactions_invoke
        self.checker_all = check_suspicious_transactions_all_currencies_invoke

    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC7_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch(ETH_ROOT + 'get_accounts')
    @requests_mock.mock()
    def test_eth_checker(self, get_accounts, mock):
        hash = 'asd'
        hash_token = 'bla'
        amount = Decimal('12')
        value = int(amount * (10**18))
        hex_val = hex(value)
        hex_val_padding = '0' * (64 - len(hex_val[2:]))
        _from = RPC7_PUBLIC_KEY_C1
        _to = '0xfc8f5591fef9fcf29effea6a83acb20fbd8d8bfe'
        _to_internal = '0xfc8finternal_addressea6a83acb20fbd8d8bfe'
        get_accounts.return_value = [_to_internal]
        bdg = Currency.objects.get(code='BDG')
        _token_address = bdg.contract_address

        etherscan_txs = {
            'result': [
                {'hash': hash,
                 'value': str(value),
                 'from': _from,
                 'timeStamp': '1518441881',
                 'to': _to},
                {'hash': hash_token,
                 'value': '0',
                 'from': _from,
                 'timeStamp': '1518441881',
                 'to': _token_address,
                 'input': '0xa9059cbb000000000000000000000000{}{}{}'.format(
                     _to[2:], hex_val_padding, hex_val[2:]
                 )},
                {'hash': hash_token + '1',
                 'value': '0',
                 'from': _from,
                 'to': _token_address,
                 'timeStamp': '1518441881',
                 'input': '0xa9059cbb000000000000000000000000{}{}{}'.format(
                     _to_internal[2:], hex_val_padding, hex_val[2:]
                 )},
                {'hash': hash_token + '2',
                 'value': '0',
                 'from': _to_internal,
                 'to': _token_address,
                 'timeStamp': '1518441881',
                 'input': '0xa9059cbb000000000000000000000000{}{}{}'.format(
                     _from[2:], hex_val_padding, hex_val[2:]
                 )},
            ]
        }
        etherscan_url = \
            'http://api.etherscan.io/api?module=account&action=txlist' \
            '&address={}&startblock=0&endblock=99999999&sort=asc' \
            '&apikey=YourApiKeyToken'.format(RPC7_PUBLIC_KEY_C1)
        mock.get(etherscan_url, json=etherscan_txs)
        self.checker.apply_async(['ETH'])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        # Second run (should not be created twice)
        self.checker.apply_async(['ETH'])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        for tx in txs:
            tx = txs.last()
            currency_code = 'ETH' if tx.tx_id == hash else 'BDG'
            self.assertEqual(tx.amount, amount)
            self.assertEqual(tx.currency.code, currency_code)
            self.assertEqual(tx.address_from, _from)
            self.assertEqual(tx.address_to, _to)
            self.assertIsNotNone(tx.time)

    @patch.dict(os.environ, {'RPC3_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC3_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC3_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC3_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC3_PORT': '0000'})
    @patch(SCRYPT_ROOT + 'call_api')
    def test_scrypt_checker(self,
                            list_transactions
                            ):
        currency_code = 'XVG'
        hash = 'asd'
        amount = Decimal('12')
        _to = 'Dverge_address'

        list_transactions.return_value = [
            {'txid': hash,
             'category': 'send',
             'address': _to,
             'time': 1518441881,
             'amount': - amount},
        ]
        self.checker.apply_async([currency_code])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 1)
        # Second run (should not be created twice)
        self.checker.apply_async([currency_code])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 1)
        for tx in txs:
            tx = txs.last()
            self.assertEqual(tx.amount, amount)
            self.assertEqual(tx.currency.code, currency_code)
            self.assertIsNone(tx.address_from)
            self.assertEqual(tx.address_to, _to)
            self.assertIsNotNone(tx.time)

    @patch('audit.tasks.generic.suspicious_transactions_checker.'
           'SuspiciousTransactionsChecker.run')
    def test_check_all(self, checker_run):
        self.checker_all.apply_async()
        currs = Currency.objects.filter(
            is_crypto=True, is_token=False
        ).exclude(code__in=['RNS', 'NANO'])
        self.assertEqual(checker_run.call_count, len(currs))
