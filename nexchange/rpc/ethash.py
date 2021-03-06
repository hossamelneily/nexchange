from nexchange.api_clients.decorators import track_tx_mapper, log_errors, \
    encrypted_endpoint
from nexchange.rpc.base import BaseRpcClient
from core.models import Address, Currency, Transaction, AddressReserve
from django.conf import settings
from decimal import Decimal
from web3 import Web3, RPCProvider
from nexchange.api_clients.mappers import RpcMapper
import os
from time import sleep
import requests
from django.core.exceptions import ValidationError


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
                    decoded_input = self._decode_transaction_input(input)
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
                'gasPrice': currency.tx_price.amount_wei,
                'gas': int(currency.tx_price.limit)
            }
        else:
            value = Web3.toWei(amount, 'ether')
            tx = {
                'from': address_from,
                'to': address_to,
                'value': value,
                'gasPrice': currency.tx_price.amount_wei,
                'gas': int(currency.tx_price.limit)
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

    def get_total_gas_price(self, currency):
        gas_price = currency.tx_price.amount_wei
        gas = currency.tx_price.limit  # noqa
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
        amount = self.get_total_gas_price(card.currency)
        return self.release_coins(main_currency, address, amount)

    def resend_funds_to_main_card(self, address, currency):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        node = currency.wallet
        total_gas = self.get_total_gas_price(currency)
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
            # Hack to deal with mysterious wallet locks
            sleep(1)
            try:
                tx_id, success = self.release_coins(currency, main_address,
                                                    amount,
                                                    address_from=address)
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

    def _decode_transaction_input(self, input):
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
        decoded_input = self._decode_transaction_input(tx_input)
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
        all_accounts_lower = [acc.lower() for acc in all_accounts]
        assert address.lower() in all_accounts_lower,\
            'Main address must be in get_accounts resp {}'.format(currency)
        return address

    # TODO: use eth node if possible, for now it's third-party server
    def _list_txs(self, node, **kwargs):
        action = kwargs.get('action', 'txlist')
        tx_count = kwargs.get('tx_count',
                              settings.RPC_IMPORT_TRANSACTIONS_COUNT)
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        address = self.get_main_address(currency)
        url = 'https://api.etherscan.io/api?module=account&action={action}&' \
              'address={address}&sort=desc&page=1&offset={tx_count}&apikey=' \
              '{etherscan_api_key}'. \
            format(action=action, address=address, tx_count=tx_count,
                   etherscan_api_key=settings.ETHERSCAN_API_KEY)
        err_msg = None
        try:
            flag = False
            res_json = requests.get(url).json()
            result = res_json.get('result')
            if not isinstance(result, list):
                flag = True
                err_msg = 'Bad respond data from etherscan'
        except requests.exceptions.ConnectionError:
            flag = True
            err_msg = 'No connection to etherscan'
        if flag:
            raise ValidationError(
                'Error: {err_msg}, url: {url}'.format(err_msg=err_msg, url=url)
            )
        else:
            return result

    def assert_tx_unique(self, currency, address, amount, **kwargs):
        action = 'txlist' if not currency.is_token else 'tokentx'
        results = self._list_txs(
            currency.wallet,
            tx_count=settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT,
            action=action
        )
        _address = getattr(address, 'address', address).lower()
        raw_amount = int(
            Decimal(str(amount)) * Decimal('1e{}'.format(currency.decimals))
        )
        for result in results:
            is_same_currency = True
            tx_input = result.get('input')
            if currency.is_token:
                addr_to = result.get('to')
                tx_amount = int(result.get('value'))
                tx_currency_code = result.get('tokenSymbol')
                is_same_currency = currency.code == tx_currency_code
            else:
                if tx_input == '0x':
                    addr_to = result.get('to')
                    tx_amount = int(result.get('value'))
                else:
                    tx_contract_address = result.get('to').lower()
                    addr_to, tx_amount = \
                        self._get_transfer_data_from_eth_input(tx_input)
                    if currency.contract_address != tx_contract_address:
                        is_same_currency = False
            if all([_address == addr_to,
                    raw_amount == tx_amount,
                    is_same_currency]):
                raise ValidationError(
                    'Transaction of {amount} {currency} to {address} already '
                    'exist.'.format(
                        amount=amount,
                        currency=currency.code,
                        address=_address
                    ))
