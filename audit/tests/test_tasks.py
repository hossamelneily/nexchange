from audit.task_summary import check_suspicious_transactions_invoke,\
    check_suspicious_transactions_all_currencies_periodic
from audit.models import SuspiciousTransactions
import requests_mock
import json
from unittest.mock import patch
from core.tests.base import ETH_ROOT, SCRYPT_ROOT, BLAKE2_ROOT, OMNI_ROOT
from core.models import Transaction, Address
import os
from decimal import Decimal
from core.models import Currency
from django.conf import settings
from ticker.tests.base import TickerBaseTestCase
from core.tests.base import TransactionImportBaseTestCase

RPC7_PUBLIC_KEY_C1 = '0xmaincard11111111111111111111111111111111'
RPC13_PUBLIC_KEY_C1 = 'rnErCcvuHdxfUEcU81NtujYv36mQ4BaSP2'


class AuditBaseTestCase(TransactionImportBaseTestCase, TickerBaseTestCase):

    def create_addresss(self, address, currency=None):
        address = Address(address=address, currency=currency)
        address.save()
        return address

    def create_withdraw_txn(self, tx_id, amount, address_from='random_from',
                            address_to='random_to', currency=None,
                            tx_type=Transaction.WITHDRAW):
        address_obj_from = self.create_addresss(address_from)
        address_obj_to = self.create_addresss(address_to)
        tx = Transaction(
            amount=amount,
            tx_id=tx_id,
            address_from=address_obj_from,
            address_to=address_obj_to,
            currency=currency,
            is_completed=True,
            is_verified=True,
            type=tx_type
        )
        tx.type = Transaction.WITHDRAW
        tx.save()
        return tx

    def get_etherscan_api_url(self, action, address, tx_count, api_key):
        return 'https://api.etherscan.io/api?module=account&action={action}&' \
               'address={address}&sort=desc&page=1&offset={tx_count}&apikey=' \
               '{etherscan_api_key}'.format(action=action, address=address,
                                            tx_count=tx_count,
                                            etherscan_api_key=api_key)


class AuditTaskTestCase(AuditBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BDGETH']
        super(AuditTaskTestCase, cls).setUpClass()

    def setUp(self):
        super(AuditTaskTestCase, self).setUp()
        RNS = Currency.objects.get(code='RNS')
        RNS.disabled = True
        RNS.save()
        self.checker = check_suspicious_transactions_invoke
        self.checker_all = \
            check_suspicious_transactions_all_currencies_periodic

    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC7_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch('orders.models.instant.Order._validate_order_amount')
    @patch(ETH_ROOT + 'get_accounts')
    @requests_mock.mock()
    def test_eth_suspicious_tx_checker(self, get_accounts,
                                       mock_validate_order_amount, mock):
        tx_hash = 'asd'
        hash_token = 'bla'
        amount = Decimal('12')
        value = int(amount * (10 ** 18))
        hex_val = hex(value)
        hex_val_padding = '0' * (64 - len(hex_val[2:]))
        _from = RPC7_PUBLIC_KEY_C1
        _to = '0xfc8f5591fef9fcf29effea6a83acb20fbd8d8bfe'
        _to2 = '0xfc8f5591fef9fcf29effea6a83acb20fbd8d8ace'
        _to_internal = '0xfc8finternal_addressea6a83acb20fbd8d8bfe'
        get_accounts.return_value = [_to_internal, RPC7_PUBLIC_KEY_C1]
        bdg = Currency.objects.get(code='BDG')
        _token_address = bdg.contract_address
        etherscan_tokentx_txs = {
            'status': '1', 'message': 'OK', 'result': [
                {"blockNumber": "5663145", "timeStamp": "1527080332",
                 "hash": hash_token + '3', "from": _from,
                 "contractAddress": _token_address, "to": _to,
                 "value": str(value), "tokenSymbol": "BDG",
                 "input": "0xa9059cbb0000000000000000000000000861d1b074eb248"
                          "9dd7878a5d6d869db5896a5f0000000000000000000000000"
                          "0000000000000000000000000de0b6b3a7640000",
                 "confirmations": "1524735"},
                {"blockNumber": "5663174", "timeStamp": "1527080768",
                 "hash": hash_token + '4', "from": _from,
                 "contractAddress": _token_address, "to": _to2,
                 "value": str(value), "tokenSymbol": "BDG",
                 "input": "0xa9059cbb0000000000000000000000000861d1b074eb248"
                          "9dd7878a5d6d869db5896a5f0000000000000000000000000"
                          "0000000000000000000027ca68754e25da8486f4",
                 "confirmations": "1524706"}
            ]
        }
        etherscan_txlist_txs = {
            'status': '1', 'message': 'OK', 'result': [
                {'hash': tx_hash,
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
                 )}
            ]}
        tx_count = settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT
        api_key = settings.ETHERSCAN_API_KEY
        etherscan_txlist_url = self.get_etherscan_api_url(
            action='txlist', address=RPC7_PUBLIC_KEY_C1, tx_count=tx_count,
            api_key=api_key
        )
        etherscan_tokentx_url = self.get_etherscan_api_url(
            action='tokentx', address=RPC7_PUBLIC_KEY_C1, tx_count=tx_count,
            api_key=api_key
        )
        mock.get(etherscan_txlist_url, json=etherscan_txlist_txs)
        mock.get(etherscan_tokentx_url, json=etherscan_tokentx_txs)
        ETH = Currency.objects.get(code='ETH')
        self._create_order(pair_name='BDGETH')
        txn_id = hash_token + '4'
        different_db_tx_amount = amount + Decimal(10)
        different_db_tx_currency = Currency.objects.get(code='BNB')
        db_tx = self.create_withdraw_txn(txn_id, different_db_tx_amount,
                                         address_from=_from, address_to=_to2,
                                         currency=different_db_tx_currency)
        self.order.withdraw_address = Address.objects.get(address=_to2)
        self.order.save()
        db_tx.order = self.order
        db_tx.save()
        self.checker.apply_async([ETH])
        sus_txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(sus_txs), 4)
        # Second run (should not be created twice)
        self.checker.apply_async([ETH])
        sus_txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(sus_txs), 4)
        for tx in sus_txs:
            currency_code = 'ETH' if tx.tx_id == tx_hash else 'BDG'
            self.assertEqual(tx.amount, - amount, tx.tx_id)
            self.assertEqual(tx.currency.code, currency_code, tx.tx_id)
            self.assertEqual(tx.address_from, _from, tx.tx_id)
            self.assertIsNotNone(tx.time, tx.tx_id)
            if tx.tx_id == db_tx.tx_id:
                # three categories: amounts mismatch, different currencies and
                # wrong spend AND address to is different
                self.assertEqual(len(tx.categories.all()), 3, tx.tx_id)
                self.assertEqual(tx.address_to, _to2, tx.tx_id)
            else:
                self.assertEqual(tx.address_to, _to, tx.tx_id)

    @patch.dict(os.environ, {'RPC3_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC3_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC3_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC3_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC3_PORT': '0000'})
    @patch(SCRYPT_ROOT + 'get_accounts')
    @patch(SCRYPT_ROOT + '_list_txs')
    def test_scrypt_suspicious_tx_checker(self, mock_list_txs,
                                          mock_get_accounts):
        mock_get_accounts.return_value = RPC7_PUBLIC_KEY_C1
        currency = Currency.objects.get(code='XVG')
        tx_hash = 'asd'
        amount = 12
        outer_address = 'Dverge_address'

        mock_list_txs.return_value = [{
            'txid': tx_hash + '1',
            'category': 'send',
            'address': outer_address,
            'time': 1518441881,
            'amount': - amount
        }, {
            'txid': tx_hash + '2',
            'category': 'receive',
            'address': outer_address,
            'time': 1518441881,
            'amount': amount
        }]
        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        # Second run (should not be created twice)
        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        for tx in txs:
            if tx.address_to:
                self.assertEqual(tx.address_to, outer_address, tx.tx_id)
                self.assertEqual(tx.amount, - amount, tx.tx_id)
                self.assertIsNone(tx.address_from, tx.tx_id)
            if tx.address_from:
                self.assertEqual(tx.address_from, outer_address, tx.tx_id)
                self.assertEqual(tx.amount, amount, tx.tx_id)
                self.assertIsNone(tx.address_to, tx.tx_id)
            self.assertEqual(tx.currency.code, currency.code, tx.tx_id)
            self.assertIsNotNone(tx.time, tx.tx_id)

    @patch.dict(os.environ, {'RPC10_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC10_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC10_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC10_USER': 'user'})
    @patch.dict(os.environ, {'RPC_RPC10_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC10_PORT': '0000'})
    @patch(OMNI_ROOT + 'get_accounts')
    @patch('nexchange.rpc.base.BaseRpcClient.call_api')
    def test_omni_suspicious_tx_checker(self, mock_call_api,
                                        mock_get_accounts):
        mock_amount = 12
        mock_get_accounts.return_value = [RPC7_PUBLIC_KEY_C1]
        currency = Currency.objects.get(code='USDT')
        outer_address = 'omni_random_address'
        tx_hash = 'tx_id_randombers'

        omni_txs = [{
            'txid': tx_hash + '1',
            'fee': '0.00002896',
            'sendingaddress': RPC7_PUBLIC_KEY_C1,
            'referenceaddress': outer_address,
            'ismine': True,
            'type_int': 0,
            'type': 'Simple Send',
            'propertyid': 31,
            'amount': str(mock_amount),
            'valid': True,
            'confirmations': 1,
            "blocktime": 1528418321
        }, {
            'txid': tx_hash + '2',
            'fee': '0.00002896',
            'sendingaddress': outer_address,
            'referenceaddress': RPC7_PUBLIC_KEY_C1,
            'ismine': True,
            'type_int': 0,
            'type': 'Simple Send',
            'propertyid': 31,
            'amount': str(mock_amount),
            'valid': True,
            'confirmations': 1,
            "blocktime": 1528418321
        }]

        def side_effect(*args):
            if args[1] == 'omni_listtransactions':
                return omni_txs
            if args[1] == 'getaddressesbyaccount':
                return [RPC7_PUBLIC_KEY_C1]

        mock_call_api.side_effect = side_effect
        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        # Second run (should not be created twice)
        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        for tx in txs:
            self.assertIn(tx.address_to, [outer_address, RPC7_PUBLIC_KEY_C1])
            if tx.address_to == outer_address:
                self.assertEqual(tx.amount, - mock_amount)
            elif tx.address_to == RPC7_PUBLIC_KEY_C1:
                self.assertEqual(tx.amount, mock_amount)
            self.assertEqual(tx.currency.code, currency.code)
            self.assertIsNotNone(tx.address_from, tx.tx_id)

    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC7_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': 'wallet'})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC8_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC8_USER': 'user'})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': '0000'})
    @requests_mock.mock()
    @patch(BLAKE2_ROOT + 'get_accounts')
    def test_blake2_suspicious_tx_checker(self, mock, mock_get_accounts):
        RPC8_URL = 'http://user:password@0.0.0.0/'
        currency = Currency.objects.get(code='NANO')
        mock_amount = 12
        outer_address = 'random_blake2_address'
        mock_get_accounts.return_value = ['our_one_of_accounts']
        tx_hash = 'tx_id_random_number'
        raw_amount = str(int(Decimal(mock_amount) * Decimal(
            '1E{}'.format(currency.decimals))))
        blake2_raw_tx = {
            'history': [{
                'type': 'send',
                'account': outer_address,
                'hash': tx_hash + '1',
                'amount': raw_amount
            }, {
                'type': 'receive',
                'account': RPC7_PUBLIC_KEY_C1,
                'hash': tx_hash + '2',
                'amount': raw_amount
            }]
        }

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_list',
                    params.get('wallet')]):
                return {'accounts': [RPC7_PUBLIC_KEY_C1]}
            if all([params.get('action') == 'account_history',
                    params.get('account'), params.get('count')]):
                return blake2_raw_tx
        mock.post(RPC8_URL, json=text_callback)

        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        # Second run (should not be created twice)
        self.checker.apply_async([currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 2)
        for tx in txs:
            # in tx
            if tx.address_to is RPC7_PUBLIC_KEY_C1:
                self.assertEqual(tx.amount, mock_amount, tx.tx_id)
            # out tx
            elif tx.address_to == outer_address:
                self.assertEqual(tx.amount, - mock_amount, tx.tx_id)
            self.assertEqual(tx.currency.code, currency.code, tx.tx_id)
            self.assertIsNone(tx.time, tx.tx_id)
            self.assertIsNone(tx.address_from, tx.tx_id)

    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': RPC13_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': 'password'})
    @patch.dict(os.environ, {'RPC_RPC13_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC13_USER': 'user'})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': '0000'})
    @requests_mock.mock()
    def test_ripple_suspicious_tx_checker(self, mock):
        RPC13_URL = 'http://user:password@0.0.0.0'
        mock_currency = Currency.objects.get(code='XRP')
        mock_amount = 12
        outer_address = 'ripple address'
        dest_tag = 1234566
        tx_id = 'tx_id_randomtransaction'
        raw_amount = str(int(mock_amount * (10 ** mock_currency.decimals)))
        ripple_tx = {'result': {
            'status': 'success',
            'transactions': [{
                "meta": {
                    "TransactionIndex": 0,
                    "TransactionResult": "tesSUCCESS",
                    "delivered_amount": raw_amount
                },
                'tx': {
                    'Account': RPC13_PUBLIC_KEY_C1,
                    'Amount': raw_amount,
                    'Destination': outer_address,
                    'DestinationTag': dest_tag,
                    'Fee': '10',
                    'Sequence': 6,
                    'TransactionType': 'Payment',
                    'hash': tx_id + '1',
                    'inLedger': 10326866,
                    'ledger_index': 10326866
                },
                'validated': True
            }, {
                "meta": {
                    "TransactionIndex": 0,
                    "TransactionResult": "tesSUCCESS",
                    "delivered_amount": raw_amount
                },
                'tx': {
                    'Account': outer_address,
                    'Amount': raw_amount,
                    'Destination': RPC13_PUBLIC_KEY_C1,
                    'DestinationTag': dest_tag,
                    'Fee': '10',
                    'Sequence': 6,
                    'TransactionType': 'Payment',
                    'hash': tx_id + '2',
                    'inLedger': 10326866,
                    'ledger_index': 10326866
                },
                'validated': True
            }, {
                "meta": {
                    "TransactionIndex": 0,
                    "TransactionResult": "tesSUCCESS",
                    "delivered_amount": raw_amount
                },
                "tx": {
                    "Account": RPC13_PUBLIC_KEY_C1,
                    "Fee": "10",
                    "Flags": 0,
                    "Sequence": 1,
                    "TakerPays": {
                        "currency": "BTC",
                        "issuer": "r9cZA1mLK5R5Am25ArfXFmqgNwjZgnfk59",
                        "value": "1"
                    },
                    "TransactionType": "OfferCreate",
                    "date": 411616880,
                    "hash": tx_id + '3',
                    "inLedger": 95405,
                    "ledger_index": 95405
                },
                "validated": True
            }]
        }}

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if params.get('method') == 'account_tx':
                return ripple_tx

        mock.post(RPC13_URL, json=text_callback)
        self.checker.apply_async([mock_currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 3)
        # Second run (should not be created twice)
        self.checker.apply_async([mock_currency])
        txs = SuspiciousTransactions.objects.filter()
        self.assertEqual(len(txs), 3)
        for tx in txs:
            if tx.address_to == outer_address:
                self.assertEqual(tx.amount, - mock_amount, tx.tx_id)
                self.assertEqual(tx.address_from, RPC13_PUBLIC_KEY_C1,
                                 tx.tx_id)
            elif tx.address_to == RPC13_PUBLIC_KEY_C1:
                self.assertEqual(tx.amount, mock_amount, tx.tx_id)
                self.assertEqual(tx.address_from, outer_address, tx.tx_id)
            self.assertEqual(tx.currency.code, mock_currency.code, tx.tx_id)

    @patch('audit.tasks.generic.suspicious_transactions_checker.'
           'SuspiciousTransactionsChecker.run')
    def test_check_all(self, checker_run):
        self.checker_all.apply_async()
        currs = Currency.objects.filter(
            is_crypto=True, is_token=False
        ).exclude(code__in=['RNS'])
        self.assertEqual(checker_run.call_count, len(currs))
