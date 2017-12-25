from .base import BaseWalletApiClient
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from .decorators import track_tx_mapper, log_errors
from core.models import Address, Currency, Transaction, AddressReserve
from django.conf import settings
from nexchange.utils import AESCipher
import os
from decimal import Decimal
from web3 import Web3, RPCProvider


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
        return '{protocol}://{user}:{passwd}@{host}:{port}'.format(**kwargs),\
               kwargs

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
        raw_pass = RpcMapper.get_raw_pw(node)
        pass_key = RpcMapper.get_key_pw(node)
        cipher = AESCipher(pass_key)
        return cipher.decrypt(raw_pass)


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
        raise NotImplementedError

    def call_api(self, node, endpoint, *args, **kwargs):
        # TODO: move unlock to decorator
        api = self.get_api(node)
        fn = self.get_fn(api, endpoint)
        try:
            rpc_pass = RpcMapper.get_pass(node)
            self.unlock(api, rpc_pass, **{'node': node})
            if not callable(fn):
                return fn
            return fn(*args, **kwargs)
        except JSONRPCException as e:
            self.logger.error('JSON RPC ERROR HOST {} ERROR {}'
                              .format(self.rpc_endpoint, str(e)))
        finally:
            try:
                self.lock(api, **{'node': node})
                pass
            except JSONRPCException:
                msg = 'Unencrypted wallet was attempted ' \
                      'to be locked node: {} endpoint: {}'.\
                    format(node, endpoint)
                self.logger.error(msg)


class ScryptRpcApiClient(BaseRpcClient):
    LOCK_WALLET = 'walletlock'
    UNLOCK_WALLET = 'walletpassphrase'

    LOCK_WALLET = 'walletlock'
    UNLOCK_WALLET = 'walletpassphrase'

    def __init__(self):
        super(ScryptRpcApiClient, self).__init__()
        self.related_nodes = ['rpc2', 'rpc3', 'rpc4', 'rpc5', 'rpc6']
        self.related_coins = ['DOGE', 'XVG', 'BCH', 'BTC', 'LTC']

    def lock(self, api, **kwargs):
        encrypt_fn = getattr(api, self.LOCK_WALLET)
        return encrypt_fn()

    def unlock(self, api, pass_phrase, **kwargs):
        decrypt_fn = getattr(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[pass_phrase, settings.WALLET_TIMEOUT])

    def get_fn(self, api, endpoint):
        return getattr(api, endpoint)

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

    def release_coins(self, currency, address, amount, **kwargs):
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

    def backup_wallet(self, currency):
        path = os.path.join(settings.WALLET_BACKUP_PATH,
                            currency.code)
        self.call_api(currency.wallet, 'backupwallet', *[path])


class EthashRpcApiClient(BaseRpcClient):

    ERC20_FUNCTIONS = {
        '0xa9059cbb': 'transfer(address,uint256)',
        '0x23b872dd': 'transferFrom(address,address,uint256)',
        '0xdd62ed3e': 'allowance(address,address)',
        '0x095ea7b3': 'approve(address,uint256)',
        '0x70a08231': 'balanceOf(address)',
        '0x313ce567': 'decimals()',
        '0x06fdde03': 'name()',
        '0x95d89b41': 'symbol()',
        '0x18160ddd': 'totalSupply()',
        '0x54fd4d50': 'version()',
    }
    ERC20_TRANSFER_FINCTIONS = ['transfer(address,uint256)']
    ENCRYPTED_METHODS = ['personal_sendTransaction', 'eth_sendTransaction']

    LOCK_WALLET = 'personal_lockAccount'
    UNLOCK_WALLET = 'personal_unlockAccount'

    def __init__(self):
        super(EthashRpcApiClient, self).__init__()
        self.related_nodes = ['rpc7']
        self.related_coins = ['ETH']
        self.encrypt = None

    def get_fn(self, api, endpoint):
        self.encrypt = True if endpoint in self.ENCRYPTED_METHODS else False
        module = endpoint.split('_')[0]
        method = endpoint.split('_')[1]
        return getattr(getattr(api, module), method)

    def lock(self, api, **kwargs):
        if not self.encrypt:
            return
        account = self.coin_card_mapper(kwargs.get('node'))
        encrypt_fn = self.get_fn(api, self.LOCK_WALLET)
        return encrypt_fn(*[account])

    def unlock(self, api, pass_phrase, **kwargs):
        if not self.encrypt:
            return
        account = self.coin_card_mapper(kwargs.get('node'))
        decrypt_fn = self.get_fn(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[account, pass_phrase, settings.WALLET_TIMEOUT])

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        params = {
            'host': kwargs.get('host'),
            'port': kwargs.get('port'),
        }
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = Web3(RPCProvider(
                **params
            ))
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def create_address(self, currency, password=None):
        node = currency.wallet
        if password is None:
            pass_env = 'RPC_{}_{}'.format(node.upper(), 'PASSWORD')
            password = os.getenv(pass_env, None)
        address = self.call_api(node, 'personal_newAccount', *[password])
        return {
            'currency': currency,
            'address': address
        }

    def get_accounts(self, currency):
        node = currency.wallet
        return self.call_api(node, 'eth_accounts')

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'code': tx['currency_code']})
        to = tx['to']
        value = tx['value']
        try:
            _address = self.get_address({'address': to})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )

        amount = \
            Decimal(str(value)) * Decimal('1e-{}'.format(_currency.decimals))

        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': amount,
            'tx_id': tx['tx_id'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return True

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'eth_getTransaction', *[tx_id])
        return tx

    def _get_tx_receipt(self, tx_id, node):
        tx = self.call_api(node, 'eth_getTransactionReceipt', *[tx_id])
        return tx

    def _get_current_block(self, node):
        return self.call_api(node, 'eth_blockNumber')

    def check_tx(self, tx_id, currency):
        if isinstance(tx_id, Transaction):
            tx_id = tx_id.tx_id
        node = currency.wallet
        tx_data = self._get_tx(tx_id, node)
        highest_block = self._get_current_block(node)
        confirmations = highest_block - tx_data.get('blockNumber')
        receipt = self._get_tx_receipt(tx_id, node)
        status = receipt.get('status', 0)
        # FIXME: Failed transaction can still be confirmed on ETH network
        if status == 0:
            confirmations = 0
        return confirmations > currency.min_confirmations, confirmations

    def _get_txs(self, node):
        return self._get_txs_from_blocks(node)

    def _get_txs_from_blocks(self, node, start_block_number=None,
                             end_block_number=None, accounts=None):
        res = []
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        currency_code = currency.code
        accounts = accounts if accounts else self.get_accounts(currency)
        if end_block_number is None:
            end_block_number = self._get_current_block(node)

        if start_block_number is None:
            start_block_number = \
                end_block_number - settings.RPC_IMPORT_BLOCK_COUNT

        for i in range(start_block_number, end_block_number + 1):
            block = self.call_api(node, 'eth_getBlock', *[i, True])
            if not block:
                continue
            transactions = block.get('transactions')
            if not all([block, transactions]):
                continue
            for tx_data in transactions:
                tx_id = tx_data.get('hash')
                main_to = tx_data.get('to')
                _from = tx_data.get('from')
                main_value = tx_data.get('value')
                if main_value == 0:
                    _currency = Currency.objects.filter(
                        contract_address=main_to).last()
                    currency_code = _currency.code if _currency else ''
                    input = tx_data.get('input')
                    decoded_input = self.decode_transaction_input(input)
                    if decoded_input[0] in self.ERC20_TRANSFER_FINCTIONS:
                        to = self._strip_address_padding(decoded_input[1][0])
                        value = int(decoded_input[1][1], 16)
                else:
                    value = main_value
                    to = main_to
                if not currency_code:
                    continue
                if all([to not in accounts]):
                    continue
                res.append({
                    'data': tx_data,
                    'currency_code': currency_code,
                    'to': to,
                    'from': _from,
                    'value': value,
                    'tx_id': tx_id
                })
        return res

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(EthashRpcApiClient, self).get_txs(node, txs)

    def _form_transaction(self, currency, address, amount, **kwargs):
        node = currency.wallet
        if isinstance(address, Address):
            address_to = address.address
        else:
            address_to = address
        address_from = kwargs.get('address_from', self.coin_card_mapper(node))

        if currency.is_token:
            value = int(
                Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
            )
            data = self.get_data_hash('transfer(address,uint256)',
                                      *[address_to, hex(value)])
            tx = {
                '_from': address_from,
                'to': currency.contract_address,
                'value': 0,
                'data': data,
                'gasPrice': settings.RPC_GAS_PRICE,
                'gas': settings.RPC_GAS_LIMIT_TOKEN
            }
        else:
            value = Web3.toWei(amount, 'ether')
            tx = {
                '_from': address_from,
                'to': address_to,
                'value': value,
                'gasPrice': settings.RPC_GAS_PRICE,
                'gas': settings.RPC_GAS_LIMIT_ETH
            }
        assert tx['gasPrice'] <= 120 * (10 ** 9)
        assert tx['gas'] <= 250000

        return tx

    def release_coins(self, currency, address, amount, **kwargs):
        tx = self._form_transaction(currency, address, amount, **kwargs)
        node = currency.wallet

        tx_id = self.call_api(node, 'eth_sendTransaction',
                              *[tx])
        success = True
        return tx_id, success

    def coin_card_mapper(self, node):
        account_env = '{}_PUBLIC_KEY_C1'.format(node.upper())
        account = os.getenv(account_env, None)
        return account

    def get_balance(self, currency, account=None):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        node = currency.wallet
        if account is None:
            account = self.coin_card_mapper(node)
        if currency.is_token:
            res = self.call_erc20_api(node, 'balanceOf(address)',
                                      currency.contract_address, *[account])
            value = int(res, 16)
        else:
            value = self.call_api(node, 'eth_getBalance', *[account])
        return Decimal(str(value)) * Decimal('1e-{}'.format(currency.decimals))

    def get_total_gas_price(self, is_token):
        gas_price = settings.RPC_GAS_PRICE
        gas =  settings.RPC_GAS_LIMIT_TOKEN if is_token else settings.RPC_GAS_LIMIT_ETH  # noqa
        return Web3.fromWei(gas_price * gas, 'ether')

    def check_card_balance(self, card_pk, **kwargs):
        card = AddressReserve.objects.get(pk=card_pk)
        currency_code = kwargs.get('currency_code', card.currency.code)
        res = self.resend_funds_to_main_card(card.address, currency_code)
        return res

    def add_gas_to_card(self, card_pk):
        card = AddressReserve.objects.get(pk=card_pk)
        node = card.currency.wallet
        address = card.address
        main_currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        amount = self.get_total_gas_price(main_currency.is_token)
        return self.release_coins(main_currency, address, amount)

    def resend_funds_to_main_card(self, address, currency):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        node = currency.wallet
        total_gas = self.get_total_gas_price(False)
        main_address = self.coin_card_mapper(node)
        balance = self.get_balance(currency, account=address)
        if currency.is_token:
            main_currency = Currency.objects.get(
                code=self.related_coins[self.related_nodes.index(node)]
            )
            main_balance = self.get_balance(main_currency, account=address)
            amount = balance
        else:
            amount = main_balance = balance - total_gas

        if any([amount <= 0, main_balance < total_gas]):
            return {'success': False, 'retry': True}
        tx_id, success = self.release_coins(currency, main_address,
                                            amount, address_from=address)
        retry = not success
        return {'success': success, 'retry': retry, 'tx_id': tx_id}

    def pad_left(self, value, width=64):
        if value[:2] == '0x':
            value = value[2:]
        return (width - len(value)) * '0' + value

    def _strip_address_padding(self, address):
        return address.replace(24 * '0', '')

    def decode_transaction_input(self, input):
        if input == '0x':
            return False, []
        sha3_method = input[:10]
        params_input = input[10:]
        params = []
        method = self.ERC20_FUNCTIONS.get(sha3_method)
        if not method:
            return False, []
        assert Web3.sha3(bytes(method, 'utf-8'))[:10] == sha3_method
        for i in range(len(params_input) // 64):
            param = '0x{}'.format(
                params_input[64 * i: 64 * (i + 1)]
            )
            params.append(param)
        return method, params
            
    def backup_wallet(self, currency):
        pass

    def get_data_hash(self, fn, *args):
        data_hash = Web3.sha3(bytes(fn, 'utf-8'))[:10]
        for arg in args:
            data_hash += self.pad_left(arg)
        return data_hash

    def call_erc20_api(self, node, fn, contract_address, *args):
        data = self.get_data_hash(fn, *args)
        tx = {
            "to": contract_address,
            "data": data
        }
        return self.call_api(node, 'eth_call', *[tx])

    def load_info(self):
        res = self.call_api('rpc7', 'eth_syncing')
        c = res['currentBlock']
        h = res['highestBlock']
        return res, h - c, c / h
 