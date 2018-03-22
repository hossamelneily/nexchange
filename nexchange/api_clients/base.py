from nexchange.utils import get_nexchange_logger
from core.models import Currency, Address, AddressReserve
from bitcoinrpc.authproxy import JSONRPCException
from django.conf import settings
from .decorators import log_errors
import requests
import json


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
        return len(txs), \
            [self.parse_tx(tx, node)
                for tx in txs if self.filter_tx(tx)]

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


class BaseTradeApiClient(BaseApiClient):

    def trade_type_rate_type_mapper(self, trade_type):
        if trade_type.upper() == 'SELL':
            return 'Bid'
        if trade_type.upper() == 'BUY':
            return 'Ask'

    def coin_address_mapper(self, code):
        if code == 'XVG':
            return settings.API3_PUBLIC_KEY_C1
        elif code == 'DOGE':
            return settings.RPC2_PUBLIC_KEY_C1

    def trade_limit(self, pair, amount, trade_type, rate=None):
        trade_fn = getattr(self, '{}_limit'.format(trade_type.lower()))
        res = trade_fn(pair, amount, rate=rate)
        return res


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

        currencies = Currency.objects.filter(is_crypto=True, disabled=False,
                                             wallet__in=self.related_nodes)
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
        unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                         user=None,
                                                         disabled=False)
        if len(unassigned_cards) == 0:
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
        return len(txs), \
            [self.parse_tx(tx, node)
                for tx in txs if self.filter_tx(tx)]

    def check_tx(self, tx, node):
        raise NotImplementedError()

    def release_coins(self, currency, address, amount, **kwargs):
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


class BaseTradeApiClient(BaseApiClient):

    def trade_type_rate_type_mapper(self, trade_type):
        if trade_type.upper() == 'SELL':
            return 'Bid'
        if trade_type.upper() == 'BUY':
            return 'Ask'

    def coin_address_mapper(self, code):
        if code == 'XVG':
            return settings.RPC3_PUBLIC_KEY_C1
        elif code == 'DOGE':
            return settings.RPC2_PUBLIC_KEY_C1

    def trade_limit(self, pair, amount, trade_type, rate=None):
        trade_fn = getattr(self, '{}_limit'.format(trade_type.lower()))
        res = trade_fn(pair, amount, rate=rate)
        return res


class Blake2Proxy:

    def __init__(self, url):
        self.url = url

    def _call_rpc(self, action, **kwargs):
        res = requests.post(self.url,
                            data=json.dumps({'action': action, **kwargs}))
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

