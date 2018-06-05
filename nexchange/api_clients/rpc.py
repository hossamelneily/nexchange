from .base import Blake2Proxy, CryptonightProxy, BaseWalletApiClient
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from .decorators import track_tx_mapper, log_errors, encrypted_endpoint
from core.models import Address, Currency, Transaction, AddressReserve
from django.conf import settings
from decimal import Decimal
from web3 import Web3, RPCProvider
from .mappers import RpcMapper
import os
from http.client import RemoteDisconnected


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


class ScryptRpcApiClient(BaseRpcClient):
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
        confirmations = tx['confirmations']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0])
        return confirmed, confirmations

    def _get_txs(self, node):
        txs = self.call_api(node, 'listtransactions',
                            *["", settings.RPC_IMPORT_TRANSACTIONS_COUNT])
        return txs

    def get_accounts(self, node):
        return self.call_api(node, 'getaddressesbyaccount', *[""])

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(ScryptRpcApiClient, self).get_txs(node, txs)

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        _address = getattr(address, 'address', address)
        tx_id = self.call_api(currency.wallet, 'sendtoaddress',
                              *[_address, amount])
        success = True
        return tx_id, success

    def get_balance(self, currency):
        balance = self.call_api(currency.wallet, 'getbalance')
        return balance

    def get_info(self, currency):
        method = 'getwalletinfo' if currency.code in ['BTC'] else 'getinfo'
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
        return super(ScryptRpcApiClient, self).health_check(currency)

    def backup_wallet(self, currency):
        path = os.path.join(settings.WALLET_BACKUP_PATH,
                            currency.code)
        self.call_api(currency.wallet, 'backupwallet', *[path])


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


class Blake2RpcApiClient(BaseRpcClient):

    UNLOCK_WALLET = 'password_enter'

    def __init__(self):
        super(Blake2RpcApiClient, self).__init__()
        self.related_nodes = ['rpc8']
        self.related_coins = ['NANO']

    def get_api(self, node):
        self.rpc_endpoint, kwargs = RpcMapper.get_rpc_addr(node)
        if self.rpc_endpoint not in self.api_cache:
            self.api_cache[self.rpc_endpoint] = Blake2Proxy(self.rpc_endpoint)
        self.api = self.api_cache[self.rpc_endpoint]
        return self.api

    def get_fn(self, api, endpoint):
        return getattr(api, endpoint)

    def lock(self, api, **kwargs):
        pass

    def unlock(self, api, pass_phrase, **kwargs):
        wallet = self.coin_wallet_mapper(kwargs.get('node'))
        decrypt_fn = getattr(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[wallet, pass_phrase])

    def get_accounts(self, node, wallet=None):
        if wallet is None:
            wallet = self.coin_wallet_mapper(node)
        return self.call_api(node, 'account_list', *[wallet])

    def create_address(self, currency, wallet=None):
        node = currency.wallet
        if wallet is None:
            wallet = self.coin_wallet_mapper(node)
        address = self.call_api(node, 'account_create', *[wallet])
        return {
            'currency': currency,
            'address': address
        }

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})

        try:
            _address = self.get_address({'address': tx['account_to']})
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
            'tx_id': tx['hash'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return tx['type'] == 'receive'

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'get_block', *[tx_id])
        return tx

    def check_tx(self, tx, currency):
        # this assumes that currency and node are one to one except uphold
        node = currency.wallet
        pending_exists = self.call_api(node, 'pending_exists', *[tx.tx_id])
        if pending_exists == '0':
            confirmed = True
            confirmations = 1
        else:
            confirmed = False
            confirmations = 0
        return confirmed, confirmations

    def _get_txs(self, node):
        txs = []
        accounts = self.get_accounts(node)
        for account in accounts:
            res = self.call_api(
                node, 'account_history',
                *[account, settings.RPC_IMPORT_TRANSACTIONS_COUNT]
            )
            txs += res
        return txs

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(Blake2RpcApiClient, self).get_txs(node, txs)

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        node = currency.wallet
        address_to = getattr(address, 'address', address)
        address_from = kwargs.get('address_from', self.coin_card_mapper(node))
        wallet = self.coin_wallet_mapper(node)
        raw_amount = str(int(
            Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
        ))

        tx_id = self.call_api(currency.wallet, 'send',
                              *[wallet, address_from, address_to, raw_amount])
        success = True
        return tx_id, success

    def coin_card_mapper(self, node):
        account_env = '{}_PUBLIC_KEY_C1'.format(node.upper())
        account = os.getenv(account_env, None)
        return account

    def coin_wallet_mapper(self, node):
        wallet_env = '{}_WALLET'.format(node.upper())
        wallet = os.getenv(wallet_env, None)
        return wallet

    def get_balance(self, currency, account=None):
        node = currency.wallet
        if account is None:
            account = self.coin_card_mapper(node)
        res = self.call_api(node, 'account_balance', *[account])
        balance_raw = res.get('balance', '0')
        pending_raw = res.get('pending', '0')
        decimals = currency.decimals
        balance = Decimal(balance_raw) / Decimal('1e{}'.format(decimals))
        pending = Decimal(pending_raw) / Decimal('1e{}'.format(decimals))
        return {'balance': balance, 'pending': pending, 'available': balance}

    def get_info(self, currency, account=None):
        node = currency.wallet
        if account is None:
            account = self.coin_card_mapper(node)
        info = self.call_api(node, 'account_info', *[account])
        return info

    def check_card_balance(self, card_pk, **kwargs):
        card = AddressReserve.objects.get(pk=card_pk)
        res = self.resend_funds_to_main_card(card.address, card.currency.code)
        return res

    def resend_funds_to_main_card(self, address, currency):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        main_address = self.get_main_address(currency)
        amount = self.get_balance(currency, account=address).get(
            'available', Decimal('0')
        )

        if amount <= 0:
            return {'success': False, 'retry': True}
        tx_id, success = self.release_coins(currency, main_address,
                                            amount, address_from=address)
        retry = not success
        return {'success': success, 'retry': retry, 'tx_id': tx_id}


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

    LOCK_WALLET = 'personal_lockAccount'
    UNLOCK_WALLET = 'personal_unlockAccount'

    def __init__(self):
        super(EthashRpcApiClient, self).__init__()
        self.related_nodes = ['rpc7']
        self.related_coins = ['ETH']
        self.account = None

    def get_fn(self, api, endpoint):
        module = endpoint.split('_')[0]
        method = endpoint.split('_')[1]
        return getattr(getattr(api, module), method)

    def lock(self, api, **kwargs):
        if not self.account:
            self.account = self.coin_card_mapper(kwargs.get('node'))
        encrypt_fn = self.get_fn(api, self.LOCK_WALLET)
        return encrypt_fn(*[self.account])

    def unlock(self, api, pass_phrase, **kwargs):
        if not self.account:
            self.account = self.coin_card_mapper(kwargs.get('node'))
        decrypt_fn = self.get_fn(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[self.account, pass_phrase,
                            settings.WALLET_TIMEOUT])

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
            password = RpcMapper.get_pass(node)
        address = self.call_api(node, 'personal_newAccount', *[password])
        return {
            'currency': currency,
            'address': address
        }

    def get_accounts(self, node):
        return self.call_api(node, 'eth_accounts')

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'code': tx['currency_code']})
        to = tx['to']
        value = tx['value']
        try:
            _address = self.get_address({'address': to.lower()})
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
        status = self._check_eth_tx_status(tx_data, receipt)
        # FIXME: Failed transaction can still be confirmed on ETH network
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0, status])
        return confirmed, confirmations

    def _get_txs(self, node):
        return self._get_txs_from_blocks(node)

    def _get_txs_from_blocks(self, node, start_block_number=None,
                             end_block_number=None, accounts=None):
        res = []
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        accounts = accounts if accounts else self.get_accounts(node)
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
                        contract_address__iexact=main_to).last()
                    currency_code = _currency.code if _currency else ''
                    input = tx_data.get('input')
                    decoded_input = self.decode_transaction_input(input)
                    try:
                        if decoded_input[0] in self.ERC20_TRANSFER_FINCTIONS:
                            to = self._strip_address_padding(
                                decoded_input[1][0]
                            )
                            value = int(decoded_input[1][1], 16)
                    except IndexError:
                        continue
                else:
                    value = main_value
                    to = main_to
                    currency_code = currency.code
                if not currency_code or not isinstance(to, str):
                    continue
                if all([to.lower() not in [acc.lower() for acc in accounts]]):
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
        address_to = getattr(address, 'address', address)
        address_from = kwargs.get('address_from', self.coin_card_mapper(node))

        if currency.is_token:
            value = int(
                Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
            )
            data = self.get_data_hash('transfer(address,uint256)',
                                      *[address_to, hex(value)])
            tx = {
                'from': address_from,
                'to': currency.contract_address,
                'value': 0,
                'data': data,
                'gasPrice': settings.RPC_GAS_PRICE,
                'gas': settings.RPC_GAS_LIMIT_TOKEN
            }
        else:
            value = Web3.toWei(amount, 'ether')
            tx = {
                'from': address_from,
                'to': address_to,
                'value': value,
                'gasPrice': settings.RPC_GAS_PRICE,
                'gas': settings.RPC_GAS_LIMIT_ETH
            }
        assert tx['gasPrice'] <= 120 * (10 ** 9)
        assert tx['gas'] <= 250000

        return tx

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        tx = self._form_transaction(currency, address, amount, **kwargs)
        self.account = tx['from']
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
        gas = settings.RPC_GAS_LIMIT_TOKEN if is_token else settings.RPC_GAS_LIMIT_ETH  # noqa
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
        amount = self.get_total_gas_price(card.currency.is_token)
        return self.release_coins(main_currency, address, amount)

    def resend_funds_to_main_card(self, address, currency):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        node = currency.wallet
        total_gas = self.get_total_gas_price(currency.is_token)
        main_address = self.get_main_address(currency)
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
        try:
            tx_id, success = self.release_coins(currency, main_address,
                                                amount, address_from=address)
            retry = not success
        except ValueError:
            return {'success': False, 'retry': True}
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

    def net_listening(self, currency):
        return self.call_api(currency.wallet, 'net_listening')

    def health_check(self, currency):
        assert self.net_listening(currency)
        return super(EthashRpcApiClient, self).health_check(currency)

    def _check_eth_tx_status(self, tx_data, tx_receipt):
        receipt_status = tx_receipt.get('status', 0) == 1
        if not receipt_status:
            return receipt_status
        tx_input = tx_data['input']
        to, value = self._get_transfer_data_from_eth_input(tx_input)
        if to and value:
            value_status = to_status = from_status = False
            _from = tx_data.get('from')
            for r_log in tx_receipt.get('logs', []):
                value_status = value == int(r_log.get('data', '0x'), 16)
                int_topics = [int(topic, 16) for topic in r_log['topics']]
                to_status = int(to, 16) in int_topics
                from_status = int(_from, 16) in int_topics
                if value_status and to_status and from_status:
                    break
        else:
            return receipt_status

        return receipt_status and value_status and to_status and from_status

    def _get_transfer_data_from_eth_input(self, tx_input):
        decoded_input = self.decode_transaction_input(tx_input)
        to, value = None, None
        if decoded_input[0] in self.ERC20_TRANSFER_FINCTIONS:
            to = self._strip_address_padding(
                decoded_input[1][0]
            )
            value = int(decoded_input[1][1], 16)
        return to, value

    def get_main_address(self, currency):
        node = currency.wallet
        address = os.getenv('{}_PUBLIC_KEY_C1'.format(node.upper()))
        all_accounts = self.get_accounts(node)
        all_accounts_lower = [acc.lower() for acc in all_accounts]  # noqa
        assert address.lower() in all_accounts_lower,\
            'Main address must be in get_accounts resp {}'.format(currency)
        return address


class ZcashRpcApiClient(ScryptRpcApiClient):
    def __init__(self):
        super(ZcashRpcApiClient, self).__init__()
        self.related_nodes = ['rpc9']
        self.related_coins = ['ZEC']

    def backup_wallet(self, currency):
        self.call_api(currency.wallet, 'backupwallet', currency)


class OmniRpcApiClient(ScryptRpcApiClient):
    def __init__(self):
        super(OmniRpcApiClient, self).__init__()
        self.related_nodes = ['rpc10']
        self.related_coins = ['USDT']

    def is_correct_token(self, tx, currency):
        if tx['propertyid'] == currency.property_id:
            return True
        else:
            return False

    def is_simple_send_type(self, tx):
        if tx['type_int'] == 0:
            return True
        else:
            return False

    def is_tx_vald(self, tx):
        return tx['valid']

    def check_tx(self, tx, currency):
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = tx['confirmations']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0,
                         self.is_correct_token(tx, currency),
                         self.is_simple_send_type(tx),
                         self.is_tx_vald(tx)])
        return confirmed, confirmations

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'code': tx['currency_code']})
        to = tx['to']
        try:
            _address = self.get_address({'address': to.lower()})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )
        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': tx['value'],
            'tx_id': tx['tx_id'],
            'tx_id_api': None,
        }

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'omni_gettransaction', *[tx_id])
        return tx

    def get_accounts(self, node):
        return self.call_api(node, 'getaddressesbyaccount', *[""])

    def get_main_address(self, currency):
        node = currency.wallet
        address = os.getenv('{}_PUBLIC_KEY_C1'.format(node.upper()))
        all_accounts = self.get_accounts(node)
        assert address in all_accounts, \
            'Main address must be in get_accounts resp {}'.format(currency)
        return address

    def _form_transaction(self, currency, address, amount, **kwargs):
        if isinstance(address, Address):
            address_to = address.address
        else:
            address_to = address
        main_address = self.get_main_address(currency)
        address_from = kwargs.get('address_from', main_address)

        tx = {
            'fromaddress': address_from,
            'toaddress': address_to,
            'propertyid': currency.property_id,
            'amount': amount
        }

        return tx

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        tx = self._form_transaction(currency, address, amount, **kwargs)
        tx_id = self.call_api(currency.wallet, 'omni_send',
                              *[tx])
        success = True
        return tx_id, success

    def get_balance(self, currency, account=None):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        if account is None:
            account = self.get_main_address(currency)
        balance = self.call_api(currency.wallet, 'omni_getbalance',
                                *[account, currency.property_id])
        return balance

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'omni_getinfo')
        return info

    def _get_txs(self, node):
        txs = self._get_txs_from_blocks(node)
        return txs

    def filter_tx(self, tx):
        return True

    def _get_current_block(self, node):
        res = self.call_api(node, 'omni_getinfo')
        return res.get('block')

    def _get_txs_from_blocks(self, node, start_block_number=None,
                             end_block_number=None, accounts=None):
        res = []
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        accounts = accounts if accounts \
            else self.call_api(node,
                               'getaddressesbyaccount',
                               '')
        if end_block_number is None:
            end_block_number = self._get_current_block(node)

        if start_block_number is None:
            start_block_number = \
                end_block_number - settings.RPC_IMPORT_BLOCK_COUNT

        for i in range(start_block_number, end_block_number + 1):
            txs_hashes = self.call_api(node, 'omni_listblocktransactions', i)
            if not txs_hashes:
                continue
            for tx_hash in txs_hashes:
                tx = self._get_tx(tx_hash, node)
                tx_id = tx.get('txid')
                main_to = tx.get('referenceaddress')
                _from = tx.get('sendingaddress')
                main_value = tx.get('amount')

                value = main_value
                to = main_to
                currency_code = currency.code
                if not currency_code or not isinstance(to, str):
                    continue
                if all([to.lower() not in [acc.lower() for acc in accounts]]):
                    continue
                res.append({
                    'data': tx,
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
        return super(ScryptRpcApiClient, self).get_txs(node, txs)
