from nexchange.api_clients.base import CryptonightProxy
from nexchange.api_clients.decorators import track_tx_mapper, log_errors, \
    encrypted_endpoint
from nexchange.rpc.base import BaseRpcClient
from core.models import Address, AddressReserve
from decimal import Decimal
from nexchange.api_clients.mappers import RpcMapper
import os
from http.client import RemoteDisconnected
import requests
from django.core.exceptions import ValidationError


class CryptonightRpcApiClient(BaseRpcClient):
    LOCK_WALLET = 'stop_wallet'
    UNLOCK_WALLET = 'open_wallet'
    EMPTY_PAYMENT_ID = '0000000000000000'

    def __init__(self):
        super(CryptonightRpcApiClient, self).__init__()
        self.related_nodes = ['rpc11']
        self.related_coins = ['XMR']

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        kwargs['wallet_port'] = self.wallet_port_mapper(node)
        kwargs['wallet_name'] = self.wallet_name_mapper(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = \
                CryptonightProxy(**kwargs)
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def wallet_port_mapper(self, node):
        wallet_port_env = 'RPC_{}_WALLET_PORT'.format(node.upper())
        wallet_port = os.getenv(wallet_port_env, None)
        return wallet_port

    def wallet_name_mapper(self, node):
        wallet_name_env = 'RPC_{}_WALLET_NAME'.format(node.upper())
        wallet_name = os.getenv(wallet_name_env, None)
        return wallet_name

    def lock(self, api, **kwargs):
        encrypt_fn = getattr(api, self.LOCK_WALLET)
        return encrypt_fn()

    def unlock(self, api, pass_phrase, **kwargs):
        decrypt_fn = getattr(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[pass_phrase])

    def get_main_address(self, currency):
        address = super(CryptonightRpcApiClient, self).\
            get_main_address(currency)
        assert address == AddressReserve.objects.get(currency=currency).address
        return address

    @encrypted_endpoint
    def create_address(self, currency):
        address = self.get_main_address(currency)
        if address is None:
            address = self.call_api(currency.wallet, 'create_address')
        return {
            'currency': currency,
            'address': address
        }

    @encrypted_endpoint
    def get_accounts(self, node, **kwargs):
        return self.call_api(node, 'getaddress')

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})
        try:
            _address = \
                self.get_address({'address': tx['address']})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )
        raw_amount = tx['amount']
        amount = Decimal(str(raw_amount)) * Decimal('1e-{}'.format(_currency.decimals))  # noqa
        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': amount,
            'payment_id': tx.get('payment_id'),
            'tx_id': tx.get('txid'),
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return True if tx.get('payment_id') != self.EMPTY_PAYMENT_ID \
            else False

    @encrypted_endpoint
    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'get_transfer_by_txid', *[tx_id])
        return tx['transfer']

    @encrypted_endpoint
    def get_current_block(self, node):
        return self.call_api(node, 'getheight')

    def get_confirmations_amount(self, tx, currency):
        node = currency.wallet
        tx_block = int(tx.get('height'))
        current_block = int(self.get_current_block(node).get('height'))
        assert current_block != 0
        confirmations = current_block - tx_block
        return confirmations

    def check_tx(self, tx, currency):
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = self.get_confirmations_amount(tx, currency)
        double_spend_seen = tx['double_spend_seen']
        confirmed = all([confirmations >= currency.min_confirmations,
                         0 < confirmations < 100, not double_spend_seen])
        return confirmed, confirmations

    @encrypted_endpoint
    def _list_txs(self, node, **kwargs):
        txs = self.call_api(node, 'get_transfers', **kwargs)
        return txs

    def _get_txs(self, node):
        res = self._list_txs(node, is_in=True, is_out=False)
        in_txs = res.get('in', [])
        return in_txs

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(CryptonightRpcApiClient, self).get_txs(node, txs)

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        _address = getattr(address, 'address', address)
        payment_id = kwargs.get('payment_id', None)
        amount_atoms = \
            Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
        amount_atoms = round(amount_atoms, 0)
        try:
            tx_id = self.call_api(currency.wallet, 'transfer',
                                  *[_address, int(amount_atoms), payment_id])
        except requests.ConnectTimeout:
            tx_id = self.call_api(currency.wallet, 'transfer',
                                  *[_address, int(amount_atoms), payment_id])
        success = True
        return tx_id, success

    @encrypted_endpoint
    def get_balance(self, currency):
        res = self.call_api(currency.wallet, 'getbalance')
        balance_raw = res['balance']
        unlocked_balance_raw = res['unlocked_balance']
        decimals = currency.decimals
        balance = Decimal(balance_raw) / Decimal('1e{}'.format(decimals))
        unlocked_balance = \
            Decimal(unlocked_balance_raw) / Decimal('1e{}'.format(decimals))
        return {'balance': balance, 'unlocked_balance': unlocked_balance}

    def get_info(self, currency):
        method = 'get_info'
        info = self.call_api(currency.wallet, method)
        return info

    # todo it's enough to check wallet method that connects to daemon
    def health_check(self, currency):
        try:
            daemon_info = self.get_info(currency)
            wallet_info = self.get_current_block(currency.wallet)
        except RemoteDisconnected:
            # First request always fails after timeout.
            # If this one fails - smth is wrong with rpc connection in general
            daemon_info = self.get_info(currency)
            wallet_info = self.get_current_block(currency.wallet)
        assert all([isinstance(daemon_info, dict),
                   isinstance(wallet_info, dict)])
        daemon_height = int(daemon_info.get('height'))
        wallet_height = int(wallet_info.get('height'))
        assert daemon_height - wallet_height == 0
        return super(CryptonightRpcApiClient, self).health_check(currency)

    def backup_wallet(self, currency):
        pass

    def assert_tx_unique(self, currency, address, amount, **kwargs):
        res = self._list_txs(
            currency.wallet,
            is_in=False, is_out=True
        )
        out_txs = res.get('out', [])
        _address = getattr(address, 'address', address)
        _amount = int(
            Decimal(amount) * Decimal('1E{}'.format(currency.decimals))
        )
        same_transactions = [
            tx for tx in out_txs if
            int(tx['amount']) == _amount and
            tx['address'] == _address
        ]
        if same_transactions:
            raise ValidationError(
                'Transaction of {amount} {currency} to {address} already '
                'exist. Tx: {tx_list}'.format(
                    amount=_amount, address=_address, currency=currency,
                    tx_list=same_transactions
                )
            )
