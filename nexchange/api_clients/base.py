from nexchange.utils import get_nexchange_logger
from core.models import Currency, Address, AddressReserve
from django.conf import settings
from .decorators import log_errors


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

    def renew_cards_reserve(self,
                            expected_reserve=settings.CARDS_RESERVE_COUNT):
        if settings.DEBUG:
            self.logger.info(
                expected_reserve,
                settings.API1_USER,
                settings.API1_PASS
            )

        currencies = Currency.objects.filter(is_crypto=True, disabled=False,
                                             wallet__in=self.related_nodes)

        for curr in currencies:
            count = AddressReserve.objects \
                .filter(user=None, currency=curr, disabled=False).count()
            while count < expected_reserve:
                address_res = self.create_address(curr)
                AddressReserve.objects.get_or_create(**address_res)
                self.logger.info(
                    "new card currency: {}, address: {}".format(
                        curr.code, address_res['address']))

                count = AddressReserve.objects \
                    .filter(user=None, currency=curr, disabled=False).count()

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
