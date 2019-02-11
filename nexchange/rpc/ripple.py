from nexchange.api_clients.decorators import track_tx_mapper, log_errors
from nexchange.rpc.base import BaseRpcClient
from core.models import Address, AddressReserve, Currency
from django.conf import settings
import os
from http.client import RemoteDisconnected
from decimal import Decimal
from nexchange.api_clients.mappers import RpcMapper
from nexchange.api_clients.base import RippleProxy
from django.core.exceptions import ValidationError


class RippleRpcApiClient(BaseRpcClient):

    def __init__(self):
        super(RippleRpcApiClient, self).__init__()
        self.related_nodes = ['rpc13']
        self.related_coins = ['XRP']

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = \
                RippleProxy(self.rpc_endpoint)
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def get_fn(self, api, endpoint):
        return getattr(api, endpoint)

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'ledger')
        return info

    def create_address(self, currency):
        main_address = self.get_main_address(currency)
        if main_address is None:
            res = self.call_api(currency.wallet, 'wallet_propose')
            return {
                'currency': currency,
                'address': res.get('account_id'),
                'secret_key': res.get('master_seed')
            }
        return {
            'currency': currency,
            'address': main_address
        }

    def get_accounts(self, node):
        currency = self.get_currency({'wallet': node})
        main_address = self.get_main_address(currency)
        return [main_address]

    def get_balance(self, currency, account=None):
        if account is None:
            account = self.get_main_address(currency)
        response = self.call_api(currency.wallet, 'account_info', account)
        balance_raw = Decimal(response.get('account_data').get('Balance'))
        decimals = currency.decimals
        balance = Decimal(balance_raw) / Decimal('1e{}'.format(decimals))
        return balance

    def _list_txs(self, node, **kwargs):
        tx_count = kwargs.get('tx_count',
                              settings.RPC_IMPORT_TRANSACTIONS_COUNT)
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        account = self.get_main_address(currency)
        resp = self.call_api(node, 'account_tx', *[account, tx_count])
        txs = [tx.get('tx') for tx in resp]
        return txs

    def _get_txs(self, node):
        in_txs = []
        txs = self._list_txs(node,
                             tx_count=settings.RPC_IMPORT_TRANSACTIONS_COUNT)
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        address = self.get_main_address(currency)
        # FIXME: There might be no Destination key
        in_txs.extend([tx for tx in txs if tx.get('Destination') == address])
        return in_txs

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'tx', *[tx_id])
        return tx

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(RippleRpcApiClient, self).get_txs(node, txs)

    def filter_tx(self, tx):
        if all([isinstance(tx.get('Amount'), str),
                tx.get('DestinationTag')]):
            return True
        else:
            return False

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})
        to = tx.get('Destination')
        try:
            _address = self.get_address({'address': to})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )
        amount = \
            Decimal(tx.get('Amount')) / \
            Decimal('1e{}'.format(_currency.decimals))
        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'destination_tag': str(tx.get('DestinationTag')),
            'amount': amount,
            'tx_id': tx.get('hash'),
            'tx_id_api': None,
        }

    def _get_wallet_key(self, currency):
        return RpcMapper.get_pass(currency.wallet)

    def _form_and_sign_transaction(self, currency, account_to, amount,
                                   **kwargs):
        if isinstance(account_to, Address):
            account_to = account_to.address
        main_address = self.get_main_address(currency)
        account_from = kwargs.get('address_from', main_address)
        value = \
            int(Decimal(amount) * Decimal('1e{}'.format(currency.decimals)))
        destination_tag = kwargs.get('destination_tag', None)
        tx = {
            "Account": account_from,
            "Amount": str(value),
            "Destination": account_to,
            "TransactionType": "Payment"
        }
        if destination_tag is not None:
            tx["DestinationTag"] = destination_tag
        secret_key = kwargs.get('secret_key', self._get_wallet_key(currency))
        tx_data = self.call_api(currency.wallet, 'sign', tx, secret_key)
        return tx_data.get('tx_blob')

    def release_coins(self, currency, address, amount, **kwargs):
        tx_blob = self._form_and_sign_transaction(
            currency, address, amount, **kwargs
        )
        tx_data = self.call_api(currency.wallet, 'submit', *[tx_blob])
        if all([tx_data.get('engine_result') == 'tesSUCCESS',
                tx_data.get('status') == 'success']):
            success = True
            tx_id = tx_data.get('tx_json').get('hash')
        else:
            success = False
            tx_id = None
        return tx_id, success

    # ripple doesn't have confirmations
    # It may be necessary to check the status of a transaction
    # repeatedly until the ledger identified by LastLedgerSequence is validated
    def check_tx(self, tx, currency):
        # this assumes that currency and node are one to one except uphold
        tx = self._get_tx(tx.tx_id, currency.wallet)
        validated = tx.get('validated')
        status = True \
            if tx.get('meta').get('TransactionResult') == 'tesSUCCESS' \
            else False
        tx_type = True if tx.get('TransactionType') == 'Payment' else False
        confirmed = True if all([validated, status, tx_type]) else False
        confirmations = 1
        return confirmed, confirmations

    def health_check(self, currency):
        try:
            info = self.get_info(currency)
        except RemoteDisconnected:
            # First request always fails after timeout.
            # If this one fails - smth is wrong with rpc connection in general
            info = self.get_info(currency)
        assert isinstance(info, dict)
        return super(RippleRpcApiClient, self).health_check(currency)

    def backup_wallet(self, currency):
        pass

    def get_main_address(self, currency):
        node = currency.wallet
        address = os.getenv('{}_PUBLIC_KEY_C1'.format(node.upper()))
        assert address == AddressReserve.objects.get(currency=currency).address
        return address

    def renew_cards_reserve(self, **kwargs):
        pass

    def assert_tx_unique(self, currency, address, amount, **kwargs):
        txs = self._list_txs(
            currency.wallet,
            tx_count=settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT
        )
        _address = getattr(address, 'address', address)
        _amount = str(int(
            Decimal(amount) * Decimal('1E{}'.format(currency.decimals))
        ))
        same_transactions = [
            tx for tx in txs if
            tx.get('Destination') == _address and
            isinstance(tx.get('Amount', None), str) and
            tx.get('Amount') == _amount
        ]
        if same_transactions:
            raise ValidationError(
                'Transaction of {amount} {currency} to {address} already '
                'exist. Tx: {tx_list}'.format(
                    amount=amount, address=_address, currency=currency,
                    tx_list=same_transactions
                )
            )
