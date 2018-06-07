from nexchange.api_clients.base import BaseWalletApiClient
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from nexchange.api_clients.mappers import RpcMapper
import os


class BaseRpcClient(BaseWalletApiClient):

    def __init__(self):
        super(BaseRpcClient, self).__init__()
        self.api_cache = {}
        self.rpc_endpoint = None

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = \
                AuthServiceProxy(self.rpc_endpoint)
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def unlock(self, api, pass_phrase, **kwargs):
        raise NotImplementedError

    def lock(self, api, **kwargs):
        raise NotImplementedError

    def encrypt(self, api):
        raise NotImplementedError

    def get_fn(self, api, endpoint):
        return getattr(api, endpoint)

    def call_api(self, node, endpoint, *args, **kwargs):
        # TODO: move unlock to decorator
        api = self.get_api(node)
        fn = self.get_fn(api, endpoint)
        try:
            if not callable(fn):
                return fn
            return fn(*args, **kwargs)
        except JSONRPCException as e:
            self.logger.error('JSON RPC ERROR HOST {} ERROR {}'
                              .format(self.rpc_endpoint, str(e)))

    def get_accounts(self, node, **kwargs):
        raise NotImplementedError

    def get_main_address(self, currency):
        node = currency.wallet
        address = os.getenv('{}_PUBLIC_KEY_C1'.format(node.upper()))
        all_accounts = self.get_accounts(node)
        assert address in all_accounts,\
            'Main address must be in get_accounts resp {}'.format(currency)
        return address
