from nexchange.utils import get_nexchange_logger
from core.models import Currency, Address
from .decorators import log_errors


class BaseApiClient:

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

    def check_tx(self, tx, node=None):
        raise NotImplementedError()

    def release_coins(self, currency, address, amount):
        raise NotImplementedError()
