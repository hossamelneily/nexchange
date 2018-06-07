from nexchange.api_clients.base import Blake2Proxy
from nexchange.api_clients.decorators import track_tx_mapper, log_errors, encrypted_endpoint
from nexchange.rpc.base import BaseRpcClient
from core.models import Address, Currency, AddressReserve
from django.conf import settings
from decimal import Decimal
from nexchange.api_clients.mappers import RpcMapper
import os


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
