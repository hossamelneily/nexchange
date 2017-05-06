from core.models import Currency
from .base import BaseApiClient
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from .decorators import track_tx_mapper, log_errors
import os


class RpcMapper:

    @classmethod
    def get_rpc_addr(cls, node):
        protocol = 'http'
        prefix = 'RPC'
        user_env = '{}_{}_{}'.format(prefix, node.upper(), 'USER')
        pass_env = '{}_{}_{}'.format(prefix, node.upper(), 'PASSWORD')
        host_env = '{}_{}_{}'.format(prefix, node.upper(), 'HOST')
        port_env = '{}_{}_{}'.format(prefix, node.upper(), 'PORT')
        kwargs = {
            'protocol': protocol,
            'user': os.getenv(user_env, 'user'),
            'passwd': os.getenv(pass_env, 'userpass'),
            'host': os.getenv(host_env, '192.168.8.7'),
            'port': os.getenv(port_env, '65223'),
        }
        return '{protocol}://{user}:{passwd}@{host}:{port}'.format(**kwargs)


class BaseRpcClient(BaseApiClient):
    UNLIMITED = 999

    def __init__(self):
        super(BaseRpcClient, self).__init__()
        self.api_cache = {}
        self.rpc_endpoint = None

    def get_api(self, node):
        self.rpc_endpoint = RpcMapper.get_rpc_addr(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = \
                AuthServiceProxy(self.rpc_endpoint)
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def call_api(self, node, endpoint, *args):
        api = self.get_api(node)
        try:
            fn = getattr(api, endpoint)
            return fn(*args)
        except JSONRPCException as e:
            self.logger.error('JSON RPC ERROR HOST {} ERROR {}'
                              .format(self.rpc_endpoint, str(e)))


class ScryptRpcApiClient(BaseRpcClient):

    def __init__(self):
        super(ScryptRpcApiClient, self).__init__()
        self.related_nodes = ['rpc1']
        self.related_coins = ['RNS']

    def create_address(self, currency):
        address = self.call_api(currency.wallet, 'getnewaddress')
        return {
            'currency': currency,
            'address': address
        }

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})
        _address = self.get_address({'address': tx['address']})

        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': ['amount'],
            # TODO: check if right type is sent by the wallet
            'time': tx['time'],
            'tx_id': tx['txid'],
        }

    def filter_tx(self, tx):
        return tx['category'] == 'receive'

    def check_tx(self, tx, node=None):
        # this assumes that currency and node are one to one except uphold
        currency = Currency.objects.get(wallet=node)
        tx = self.call_api(node, 'gettransaction', *[tx.tx_id])
        return tx['confirmations'] > currency.min_confirmations

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self.call_api(node, 'listtransactions',
                            *["", self.UNLIMITED, self.start])
        return txs

    def release_coins(self, currency, address, amount):
        tx_id = self.call_api(currency.wallet, 'sendtoaddress',
                              *[address, amount])
        return tx_id
