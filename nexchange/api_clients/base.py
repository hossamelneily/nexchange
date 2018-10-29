from nexchange.utils import get_nexchange_logger
from core.models import Currency, Address, AddressReserve
from bitcoinrpc.authproxy import JSONRPCException
from requests.auth import HTTPDigestAuth
from django.conf import settings
from .decorators import log_errors
import inspect
import requests
import json
import time


class BaseApiClient:

    TX_ID_FIELD_NAME = 'tx_id'

    def __init__(self):
        self.start = 0
        self.old_start = 0
        self.api = None
        self.related_nodes = []
        self.logger = get_nexchange_logger(self.__class__.__name__)
        self.mapper = None
        self.cache = {}

    def revert_tx_mapper(self):
        self.mapper.start = self.start
        self.mapper.save()

    def get_currency(self, lookup):
        return self.get_cached_obj(Currency, lookup)

    def get_address(self, lookup):
        # get or create or catch?
        return self.get_cached_obj(Address, lookup)

    @log_errors
    def get_cached_obj(self, obj, lookup):
        cache_id = str(hash(frozenset(lookup.items())))
        if cache_id not in self.cache:
            self.cache[cache_id] = obj.objects.get(
                **lookup
            )
        return self.cache[cache_id]

    def get_api(self, currency):
        raise NotImplementedError()

    def create_address(self, currency):
        raise NotImplementedError()

    def parse_tx(self, tx, node=None):
        raise NotImplementedError()

    def filter_tx(self, tx):
        raise NotImplementedError()

    def get_txs(self, node=None, txs=None):
        _txs = [self.parse_tx(tx, node) for tx in txs
                if self.filter_tx(tx)]
        txs = [tx for tx in _txs if tx is not None]
        return len(txs), txs

    def check_tx(self, tx, node):
        raise NotImplementedError()

    def release_coins(self, currency, address, amount):
        raise NotImplementedError()

    def resend_funds_to_main_card(self, card_id, curr_code):
        raise NotImplementedError

    def check_card_balance(self, card_pk):
        card = AddressReserve.objects.get(pk=card_pk)
        res = self.resend_funds_to_main_card(card.card_id, card.currency.code)
        return res

    def get_card_validity(self, wallet):
        raise NotImplementedError()

    def retry(self, tx):
        self.logger.warning(
            'retry is not implemented for currency {}. Tx: {}'.format(
                tx.currency, tx))
        return {'success': False, 'retry': False}

    def get_main_address(self, currency):
        raise NotImplementedError()

    def health_check(self, currency):
        return True


class BaseWalletApiClient(BaseApiClient):

    def renew_cards_reserve(self,
                            expected_reserve=settings.CARDS_RESERVE_COUNT,
                            renew_curr_of_disabled_pairs=False):
        if settings.DEBUG:
            self.logger.info(
                expected_reserve,
                settings.API1_USER,
                settings.API1_PASS
            )

        currencies = Currency.objects.filter(
            is_crypto=True, disabled=False, wallet__in=self.related_nodes
        ).exclude(code__in=['XMR', 'XRP'])
        if not renew_curr_of_disabled_pairs:
            currencies = [
                curr for curr in currencies if curr.is_quote_of_enabled_pair_for_test  # noqa
            ]

        for curr in currencies:
            renewed = False
            count = AddressReserve.objects \
                .filter(user=None, currency=curr, disabled=False).count()
            while count < expected_reserve:
                renewed = True
                address_res = self.create_address(curr)
                AddressReserve.objects.get_or_create(**address_res)
                self.logger.info(
                    "new card currency: {}, address: {}".format(
                        curr.code, address_res['address']))
                count = AddressReserve.objects \
                    .filter(user=None, currency=curr, disabled=False).count()
            if renewed:
                self.backup_wallet(curr)

    def create_user_wallet(self, user, currency):
        one_card_currencies = ['XMR', 'XRP']
        unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                         user=None,
                                                         disabled=False)
        if currency.code in one_card_currencies:
            unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                             disabled=False)

        if len(unassigned_cards) == 0 \
                and currency.code not in one_card_currencies:
            self.logger.warning('instance {} has no reserve cards available'
                                ' for {} calling renew_cards_reserve()'
                                .format(user, currency))

            self.renew_cards_reserve(
                expected_reserve=settings.EMERGENCY_CARDS_RESERVE_COUNT)
            unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                             user=None,
                                                             disabled=False)

        if unassigned_cards:
            # FIFO
            card = unassigned_cards.earliest('id')
            card.user = user
            try:
                address = Address.objects.get(address=card.address)
            except Address.DoesNotExist:
                address = Address(
                    address=card.address,
                    user=card.user,
                    currency=currency,
                    type=Address.DEPOSIT,
                    reserve=card
                )
            address.save()
            card.save()
            return card, address
        else:
            self.logger.error('instance {} has no cards available'.format(
                currency))
        return None, None

    def replace_wallet(self, user, currency_code):
        currency = Currency.objects.get(code=currency_code)
        old_wallets = user.addressreserve_set.filter(
            user=user, currency=currency, disabled=False
        )
        for old_wallet in old_wallets:
            addresses = old_wallet.addr.all()
            for address in addresses:
                address.disabled = True
                address.user = None
                address.save()
            old_wallet.disabled = True
            old_wallet.user = None
            old_wallet.save()
        res = self.create_user_wallet(user, currency)
        return res

    def backup_wallet(self, currency):
        pass

    def get_api(self, currency):
        raise NotImplementedError()

    def create_address(self, currency):
        raise NotImplementedError()

    def parse_tx(self, tx, node=None):
        raise NotImplementedError()

    def filter_tx(self, tx):
        raise NotImplementedError()

    def check_tx(self, tx, node):
        raise NotImplementedError()

    def release_coins(self, currency, address, amount, **kwargs):
        raise NotImplementedError()

    def resend_funds_to_main_card(self, card_id, curr_code):
        raise NotImplementedError

    def get_card_validity(self, wallet):
        raise NotImplementedError()


class BaseTradeApiClient(BaseApiClient):

    def trade_type_rate_type_mapper(self, trade_type):
        if trade_type.upper() == 'SELL':
            return 'Bid'
        if trade_type.upper() == 'BUY':
            return 'Ask'

    def trade_limit(self, pair, amount, trade_type, rate=None):
        trade_fn = getattr(self, '{}_limit'.format(trade_type.lower()))
        res = trade_fn(pair, amount, rate=rate)
        return res


class Blake2Proxy:

    def __init__(self, url, timeout=1):
        self.url = url
        self.timeout = timeout

    def _call_rpc(self, action, **kwargs):
        try:
            res = requests.post(self.url,
                                data=json.dumps({'action': action, **kwargs}),
                                timeout=self.timeout)
        except requests.ConnectTimeout:
            raise JSONRPCException('Timeout, Blake2 wallet might be down')
        if res.status_code != 200:
            raise JSONRPCException('Bad status code: {}'.format(res))
        return res.json()

    def block_count(self):
        return self._call_rpc('block_count')

    def account_balance(self, account):
        kwargs = {'account': account}
        res = self._call_rpc('account_balance', **kwargs)
        if 'balance' not in res:
            raise JSONRPCException('Bad account balance response: {}'.format(
                res))
        return res

    def account_info(self, account):
        kwargs = {'account': account}
        return self._call_rpc('account_info', **kwargs)

    def account_create(self, wallet):
        kwargs = {'wallet': wallet}
        res = self._call_rpc('account_create', **kwargs)
        account = res.get('account')
        if not account:
            raise JSONRPCException('Account is None. Response:{}'.format(res))
        return account

    def account_list(self, wallet):
        kwargs = {'wallet': wallet}
        res = self._call_rpc('account_list', **kwargs)
        accounts = res.get('accounts')
        if not accounts:
            raise JSONRPCException(
                'Bad list accounts response. Response:{}'.format(res)
            )
        return accounts

    def key_create(self):
        return self._call_rpc('key_create')

    def wallet_create(self):
        return self._call_rpc('wallet_create')

    def wallet_balance_total(self, wallet):
        kwargs = {'wallet': wallet}
        return self._call_rpc('account_balance', **kwargs)

    def send(self, wallet, source, destination, amount):
        kwargs = {
            "wallet": wallet,
            "source": source,
            "destination": destination,
            "amount": amount
        }
        res = self._call_rpc('send', **kwargs)
        block = res.get('block')
        if not block:
            raise JSONRPCException(
                'No block in response: {}'.format(res)
            )
        return block

    def history(self, hash, count):
        kwargs = {'hash': hash, 'count': str(count)}
        res = self._call_rpc('history', **kwargs)
        history = res.get('history')
        if not history:
            history = []
        return history

    def get_block(self, hash):
        res = self.history(hash, 1)
        if not res:
            return None
        else:
            return res[0]

    def account_history(self, account, count):
        kwargs = {'account': account, 'count': str(count)}
        res = self._call_rpc('account_history', **kwargs)
        history = res.get('history')
        if not history:
            history = []
        else:
            for tx in history:
                tx['account_to'] = account
        return history

    def block(self, hash):
        kwargs = {'hash': hash}
        return self._call_rpc('block', **kwargs)

    def blocks_info(self, hashes):
        kwargs = {'hashes': hashes}
        return self._call_rpc('blocks_info', **kwargs)

    def pending_exists(self, hash):
        kwargs = {'hash': hash}
        res = self._call_rpc('pending_exists', **kwargs)
        return res.get('exists')

    def password_enter(self, wallet, password):
        kwargs = {'wallet': wallet, 'password': password}
        return self._call_rpc('password_enter', **kwargs)


class CryptonightProxy:
    def __init__(self, timeout=3, max_call_amount=3, **kwargs):
        self.part_url = '{protocol}://{host}:'.format(**kwargs)
        self.port = kwargs.get('port')
        self.wallet_name = kwargs.get('wallet_name')
        self.wallet_port = kwargs.get('wallet_port')
        self.user = kwargs.get('user')
        self.password = kwargs.get('passwd')
        self.timeout = timeout
        self.max_call_amount = max_call_amount

    def _call_rpc(self, method, **kwargs):
        caller_func_name = inspect.stack()[1][3]
        port = self.port if \
            caller_func_name in ['get_info', 'getblockcount'] \
            else self.wallet_port
        self.url = self.part_url + port + '/json_rpc'
        try:
            for _ in range(self.max_call_amount):
                res = requests.post(
                    self.url,
                    data=json.dumps({'method': method, **kwargs}),
                    auth=HTTPDigestAuth(self.user, self.password),
                    timeout=self.timeout
                )
                if not res.json().get('error'):
                    break
                else:
                    time.sleep(1)
        except requests.ConnectTimeout:
            raise JSONRPCException('Timeout, Cryptonight wallet might be down')
        if res.status_code != 200:
            raise JSONRPCException('Bad status code: {}'.format(res))
        try:
            return res.json()['result']
        except KeyError:
            return res.json()

    def store(self):
        pass
        # return self._call_rpc('store')

    def getaddress(self):
        res = self._call_rpc('getaddress')
        accounts = [r.get('address') for r in res.get('addresses')]
        return accounts

    def get_info(self):
        return self._call_rpc('get_info')

    def getblockcount(self):
        return self._call_rpc('getblockcount')

    def create_wallet(self, filename, password):
        kwargs = {'params': {'filename': filename,
                             'password': password,
                             'language': 'English'}}
        return self._call_rpc('create_wallet', **kwargs)

    def open_wallet(self, password):
        try:
            self._call_rpc('getheight')
            return
        except Exception:
            kwargs = {'params': {'filename': self.wallet_name,
                                 'password': password}}
            self._call_rpc('open_wallet', **kwargs)

    def stop_wallet(self):
        return self._call_rpc('store')

    def getbalance(self):
        return self._call_rpc('getbalance')

    def create_address(self):
        kwargs = {'params': {'account_index': 0}}
        address = self._call_rpc('create_address', **kwargs).get('address')
        if not address:
            raise JSONRPCException('Account is None.')
        else:
            return address

    def get_transfers(self, is_in):
        kwargs = {'params': {'pool': True, 'in': is_in}}
        return self._call_rpc('get_transfers', **kwargs)

    def transfer(self, address, amount, payment_id=None):
        # NOTE transfer can be done to multiple addresses at the time
        kwargs = {'params': {
            "destinations": [{
                "amount": amount,
                "address": address,
            }],
            "payment_id": payment_id,
            "mixin": 4,
            "get_tx_key": True}
        }
        return self._call_rpc('transfer', **kwargs).get('tx_hash')

    def get_transfer_by_txid(self, txid):
        kwargs = {'params': {'txid': txid}}
        return self._call_rpc('get_transfer_by_txid', **kwargs)

    def getheight(self):
        return self._call_rpc('getheight')


class RippleProxy:

    def __init__(self, url, timeout=2):
        self.url = url
        self.timeout = timeout

    def _call_rpc(self, method, **kwargs):
        try:
            res = requests.post(self.url,
                                data=json.dumps({'method': method, **kwargs}),
                                timeout=self.timeout)
        except requests.ConnectTimeout:
            raise JSONRPCException('Timeout, Ripple wallet might be down')
        if res.status_code != 200:
            raise JSONRPCException('Bad status code: {}'.format(res))
        try:
            return res.json()['result']
        except KeyError:
            return res.json()

    def ledger(self):
        kwargs = {"params": []}
        return self._call_rpc('ledger', **kwargs)

    def wallet_propose(self, secret_key=None):
        if secret_key is not None:
            kwargs = {"params": [{
                "passphrase": secret_key
            }]}
            return self._call_rpc('wallet_propose', **kwargs)
        else:
            return self._call_rpc('wallet_propose')

    def account_info(self, account):
        kwargs = {"params": [{
            "account": account,
            "strict": True,
            "ledger_index": "current",
            "queue": True
        }]}
        return self._call_rpc('account_info', **kwargs)

    def account_tx(self, account, count):
        kwargs = {"params": [{
            "account": account,
            "binary": False,
            "ledger_index_max": -1,
            "ledger_index_min": -1,
            "limit": count
        }]}
        return self._call_rpc('account_tx', **kwargs).get('transactions', None)

    def tx(self, tx_id):
        kwargs = {"params": [{
            "transaction": tx_id,
            "binary": False
        }]}
        return self._call_rpc('tx', **kwargs)

    def sign(self, tx, secret_key):
        kwargs = {"params": [
            {
                "offline": False,
                "secret": secret_key,
                "tx_json": tx
            }
        ]}
        return self._call_rpc('sign', **kwargs)

    def submit(self, tx_blob):
        kwargs = {"params": [{
            "tx_blob": tx_blob
        }]}
        return self._call_rpc('submit', **kwargs)
