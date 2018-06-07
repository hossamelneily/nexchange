from nexchange.api_clients.base import CryptonightProxy
from nexchange.api_clients.decorators import track_tx_mapper, log_errors, encrypted_endpoint
from nexchange.rpc.base import BaseRpcClient
from core.models import Address
from decimal import Decimal
from nexchange.api_clients.mappers import RpcMapper
import os
from http.client import RemoteDisconnected


class CryptonightRpcApiClient(BaseRpcClient):
    LOCK_WALLET = 'stop_wallet'
    UNLOCK_WALLET = 'open_wallet'

    def __init__(self):
        super(CryptonightRpcApiClient, self).__init__()
        self.related_nodes = ['rpc11']
        self.related_coins = ['XMR']

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        wallet_port = self.wallet_port_mapper(node)
        wallet_name = self.wallet_name_mapper(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = \
                CryptonightProxy(wallet_name, wallet_port, **kwargs)
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

    @encrypted_endpoint
    def create_address(self, currency):
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
            'time': tx['timestamp'],
            'tx_id': tx['txid'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return True

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'get_transfer_by_txid', *[tx_id])
        return tx['transfer']

    @encrypted_endpoint
    def get_current_block(self, node):
        return self.call_api(node, 'getheight')

    def get_confirmations_amount(self, tx, currency):
        node = currency.wallet
        tx_block = tx.get('height')
        current_block = self.get_current_block(node).get('height')
        return current_block - tx_block

    def check_tx(self, tx, currency):
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = self.get_confirmations_amount(tx, currency)
        double_spend_seen = tx['double_spend_seen']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0, not double_spend_seen])
        return confirmed, confirmations

    @encrypted_endpoint
    def _get_txs(self, node, is_in=True):
        txs = self.call_api(node, 'get_transfers', is_in)
        return txs['in']

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(CryptonightRpcApiClient, self).get_txs(node, txs)

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        _address = getattr(address, 'address', address)
        payment_id = kwargs.get('payment_id')
        amount_atoms = \
            Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
        amount_atoms = round(amount_atoms, 0)
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

    def health_check(self, currency):
        try:
            info = self.get_info(currency)
        except RemoteDisconnected:
            # First request always fails after timeout.
            # If this one fails - smth is wrong with rpc connection in general
            info = self.get_info(currency)
        assert isinstance(info, dict)
        return super(CryptonightRpcApiClient, self).health_check(currency)

    def backup_wallet(self, currency):
        pass
