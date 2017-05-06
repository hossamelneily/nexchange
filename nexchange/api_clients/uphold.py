from .base import BaseApiClient
from uphold import Uphold
from nexchange.utils import get_traceback
from django.conf import settings
from core.models import Address, AddressReserve
from .decorators import track_tx_mapper, log_errors


class UpholdApiClient(BaseApiClient):

    def __init__(self):
        super(UpholdApiClient, self).__init__()
        # Usually coins and nodes are one-to-one
        # but uphold provide all transactions as one
        self.related_coins = ['BTC', 'ETH', 'LTC']
        self.related_nodes = ['api1']
        self.api = self.get_api()

    def get_api(self, currency=None):
        if not self.api:
            self.api = Uphold(settings.API1_IS_TEST)
            self.api.auth_basic(settings.API1_USER, settings.API1_PASS)
        return self.api

    def create_address(self, currency):
        card = self._new_card(currency.code)
        address = self._new_address(card['id'], currency.name)

        return {
            'card_id': card['id'],
            'currency': currency,
            'address': address['id']
        }

    def coin_card_mapper(self, code):
        # TODO: take from user cards
        if code == 'BTC':
            return settings.API1_ID_C1
        elif code == 'LTC':
            return settings.API1_ID_C2
        elif code == 'ETH':
            return settings.API1_ID_C3
        else:
            raise ValueError(
                'Card for type {} not found'.format(code))

    def release_coins(self, currency, address, amount):
        card = self.coin_card_mapper(currency.code)
        try:
            txn_id = self.api.prepare_txn(card, address,
                                          amount, currency.code)
            res = self.api.execute_txn(card, txn_id)
            self.logger.info('uphold res: {}'.format(res))
            return txn_id
        except Exception as e:
            self.logger.error('error {} tb {}'.format(e, get_traceback()))

    def _new_card(self, currency):
        """
        Create a new card
        """

        fields = {
            'label': 'User card',
            'currency': currency,
        }

        return self.api._post('/me/cards/', fields)

    def _new_address(self, card_id, network):
        """
        Add to card address
        """

        fields = {
            'network': network,
        }
        return self.api._post('/me/cards/{}/addresses'.format(card_id), fields)

    @track_tx_mapper
    @log_errors
    def get_txs(self, node=None, txs=None):
        txs = self.api.get_transactions()
        return super(UpholdApiClient, self).get_txs(node, txs)

    def filter_tx(self, tx):
        return tx.get('type') == 'deposit'

    def parse_tx(self, tx, node=None):
        try:
            _currency = self.get_currency(
                {'code': tx['destination']['currency']}
            )
            _address = self.get_address(
                {'reserve__card_id': tx['destination']['CardId']}
            )
            # not always there
            tx_id = tx.get('params', {}).get('txid', None)

            return {
                # required
                'currency': _currency,
                'address_to': _address,
                'amount': tx['destination']['amount'],
                # TODO: check if right type is sent by UPHOLDz
                'time': tx.get('createdAt'),
                'tx_id_api': tx['id'],
                'tx_id': tx_id,
            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(tx, str(e)))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(tx, str(e)))
        except Address.DoesNotExist as e:
            self.logger.error("Unknown deposit address"
                              .format(tx, str(e)))
        except AddressReserve.DoesNotExist as e:
            self.logger.error("Unknown reserve address"
                              .format(tx, str(e)))

    def check_tx(self, tx, node=None):
        if not tx:
            return False

        res = self.api.get_reserve_transaction(tx.tx_id_api)
        if not tx.tx_id:
            tx_id = res.get('params', {}).get('txid')
            if tx_id is not None:
                tx.tx_id = tx_id
                tx.save()
        self.logger.info("status: {}".format(res.get('status')))
        return res.get('status') == 'completed'