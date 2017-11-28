from .base import BaseApiClient
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from .decorators import track_tx_mapper, log_errors
from core.models import Address
from django.conf import settings
from nexchange.utils import AESCipher
import os


class RpcMapper:
    PWS = {
        'rpc1': 'ove9n97G6tv3N8WUFdQKtgugeMGpqkYQmoHZI+jXl5rNAnAkT0Hgg'
                'F8jDuVsgXZS/QjETkQuMihsLqIDSojcRmH7piN8BSafOFG36GijxZo=',
        'rpc2': '8b2Dqw+FKwZ1pv/sAtsJUVKlz/z33zdRrivkiRIpVHWTXlilCxeYW'
                'DeQ8AjcyVK7bXReUqchn8pKAqbLYN7mG0CE+i81Ka8x3aYGaBF1hLY=',
        'rpc3': 'r7MC29tWNB1MM8elBEqrMn9IDUuPT3nzS08htosaBaJxixBFk4qsQa'
                '/aULRB/LSN6JlLu3Lr3bumPdWBc1ossuxb1/d8Mswy+MJuwJ3QBgc=',
        'rpc4': 'S5iAXq8gKpAFDMFiPzjEgVlw5vnycE4e1+A2xEBS464b2xLyayiinW'
                'qsn9f4EKFuRifZdZnBHmPKvT7iIpEOJJCNwwsonmysPDIyUURLoy4=',
        'rpc5': 'Z0DkkAwJqPJ7dx6ykAOT5lqwY5VpYlG16yhL4bU4D9zi4u4jQeqf3Pdc'
                '0KdE7f6nMdVX7QYhzwZddKlXK9zZfiiR2OutX6VLZuQmTEl4fJ0=',
        'rpc6': 'DCz4BziQRj7o+gwK2POJtcfNwVn++GXJ6Y80P2frgCU6hsMwcu1022'
                'AyHTlm7nDeBSbwir/B5qWJTrWrLDMxBNfW8MzpVMrd7fk82sPTzGU=',
        'rpc7': 'PbGnX+pDzdNZOVZ9EefGrBFMw9c8oTJxddtWsjbNINDJOai5zvK3spG'
                'YWg/yNaX+S3wjX7t0K1bl/GgZZtxSKU7OXrXQqoPjMUil6JxU7+Q=',
    }

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
            'user': os.getenv(user_env, settings.DEFAULT_RPC_USER),
            'passwd': os.getenv(pass_env, settings.DEFAULT_RPC_PASS),
            'host': os.getenv(host_env, settings.DEFAULT_RPC_HOST),
            'port': os.getenv(port_env, None),
        }
        return '{protocol}://{user}:{passwd}@{host}:{port}'.format(**kwargs)

    @classmethod
    def get_raw_pw(cls, node):
        return cls.PWS[node]


    @classmethod
    def get_key_pw(cls, node):
        prefix = 'RPC'
        env = '{}_{}_{}'.format(prefix, node.upper(), 'K')
        return os.getenv(env)

    @classmethod
    def get_pass(cls, node):
        raw_pass = RpcMapper.get_raw_pw
        pass_key = RpcMapper.get_key_pw(node)
        cipher = AESCipher(pass_key)
        return cipher.decrypt(raw_pass)


class BaseRpcClient(BaseApiClient):
    LOCK_WALLET = 'walletlock'
    UNLOCK_WALLET = 'walletpassphrase'

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

    def unlock(self, api, pass_phrase):
        raise NotImplementedError

    def lock(self, api):
        raise NotImplementedError

    def encrypt(self, api):
        raise NotImplementedError

    def call_api(self, node, endpoint, *args):
        # TODO: move unlock to decorator
        api = self.get_api(node)
        fn = getattr(api, endpoint)
        try:
            rpc_pass = RpcMapper.get_pass(node)
            self.unlock(api, rpc_pass)
            return fn(*args)
        except JSONRPCException as e:
            self.logger.error('JSON RPC ERROR HOST {} ERROR {}'
                              .format(self.rpc_endpoint, str(e)))
        finally:
            try:
                self.lock(api)
            except JSONRPCException:
                msg = 'Unencrypted wallet was attempted ' \
                      'to be locked node: {} endpoint: {}'.\
                    format(node, endpoint)
                self.logger.error(msg)


class ScryptRpcApiClient(BaseRpcClient):

    def __init__(self):
        super(ScryptRpcApiClient, self).__init__()
        self.related_nodes = ['rpc2', 'rpc3', 'rpc4', 'rpc5', 'rpc6']
        self.related_coins = ['DOGE', 'XVG', 'BCH', 'BTC', 'LTC']

    def lock(self, api):
        encrypt_fn = getattr(api, self.LOCK_WALLET)
        return encrypt_fn()

    def unlock(self, api, pass_phrase):
        decrypt_fn = getattr(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[pass_phrase, settings.WALLET_TIMEOUT])

    def create_address(self, currency):
        address = self.call_api(currency.wallet, 'getnewaddress')
        return {
            'currency': currency,
            'address': address
        }

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})

        try:
            _address = self.get_address({'address': tx['address']})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )

        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': tx['amount'],
            # TODO: check if right type is sent by the wallet
            'time': tx['time'],
            'tx_id': tx['txid'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return tx['category'] == 'receive'

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'gettransaction', *[tx_id])
        return tx

    def check_tx(self, tx, currency):
        # this assumes that currency and node are one to one except uphold
        tx = self._get_tx(tx.tx_id, currency.wallet)
        return tx['confirmations'] > currency.min_confirmations, tx[
            'confirmations']

    def _get_txs(self, node):
        txs = self.call_api(node, 'listtransactions',
                            *["", settings.RPC_IMPORT_TRANSACTIONS_COUNT])
        return txs

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(ScryptRpcApiClient, self).get_txs(node, txs)

    def release_coins(self, currency, address, amount):
        tx_id = self.call_api(currency.wallet, 'sendtoaddress',
                              *[address.address, amount])
        success = True
        return tx_id, success

    def get_balance(self, currency):
        balance = self.call_api(currency.wallet, 'getbalance')
        return balance

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'getinfo')
        return info


class EthashRpcApiClient(BaseRpcClient):

    def __init__(self):
        super(EthashRpcApiClient, self).__init__()
        self.related_nodes = ['rpc7']
        self.related_coins = ['ETH']

    def create_address(self, currency):
        address = self.call_api(currency.wallet, 'getnewaddress')
        return {
            'currency': currency,
            'address': address
        }

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})

        try:
            _address = self.get_address({'address': tx['address']})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )

        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': tx['amount'],
            # TODO: check if right type is sent by the wallet
            'time': tx['time'],
            'tx_id': tx['txid'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return tx['category'] == 'receive'

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'gettransaction', *[tx_id])
        return tx

    def check_tx(self, tx, currency):
        # this assumes that currency and node are one to one except uphold
        tx = self._get_tx(tx.tx_id, currency.wallet)
        return tx['confirmations'] > currency.min_confirmations, tx[
            'confirmations']

    def _get_txs(self, node):
        txs = self.call_api(node, 'listtransactions',
                            *["", settings.RPC_IMPORT_TRANSACTIONS_COUNT])
        return txs

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(EthashRpcApiClient, self).get_txs(node, txs)

    def release_coins(self, currency, address, amount):
        tx_id = self.call_api(currency.wallet, 'sendtoaddress',
                              *[address.address, amount])
        success = True
        return tx_id, success

    def get_balance(self, currency):
        balance = self.call_api(currency.wallet, 'getbalance')
        return balance

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'getinfo')
        return info
