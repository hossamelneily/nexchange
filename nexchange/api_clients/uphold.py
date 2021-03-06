from .base import BaseApiClient
from uphold import Uphold
from nexchange.utils import get_traceback
from django.conf import settings
from core.models import Address, AddressReserve, Currency
from decimal import Decimal
from .decorators import track_tx_mapper, log_errors


class UpholdApiClient(BaseApiClient):

    TX_ID_FIELD_NAME = 'tx_id_api'

    def __init__(self):
        super(UpholdApiClient, self).__init__()
        # Usually coins and nodes are one-to-one
        # but uphold provide all transactions as one
        self.related_coins = settings.API1_COINS
        self.related_nodes = ['api1']
        self.api = self.get_api()

    def get_api(self, currency=None):
        if not self.api:
            self.api = Uphold(settings.API1_IS_TEST)
            self.api.auth_pat(settings.API1_PAT)
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
        elif code == 'BCH':
            return settings.API1_ID_C4
        else:
            raise ValueError(
                'Card for type {} not found'.format(code))

    def address_name_mapper(self, code):
        if code == 'BTC':
            return 'bitcoin'
        elif code == 'LTC':
            return 'litecoin'
        elif code == 'ETH':
            return 'ethereum'
        elif code == 'BCH':
            return 'bitcoin-cash'
        else:
            raise ValueError(
                'Address name for {} not found'.format(code))

    def release_coins(self, currency, address, amount, card=None):
        if card is None:
            card = self.coin_card_mapper(currency.code)
        try:
            txn_id = self.api.prepare_txn(card, address,
                                          amount, currency.code)
            res = self.api.execute_txn(card, txn_id)
            self.logger.info('uphold res: {}'.format(res))
            success = res.get('code') != 'validation_failed'
            if not success:
                self.logger.warning('Cannot execute Uphold txn, Check Funds '
                                    '(need {} {})'.format(currency, amount))
            return txn_id, success
        except Exception as e:
            self.logger.error('error {} tb {}'.format(e, get_traceback()))
            return None, False

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
            try:
                _address = self.get_address(
                    {'reserve__card_id': tx['destination']['CardId']}
                )
            except Address.DoesNotExist:
                _address = None
                self.logger.warning(
                    'CardId:does not exist in DB. tx data:{}'.format(tx)
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
                try:
                    tx.tx_id = tx_id
                    tx.save()
                except Exception:
                    self.logger.info('Bad txid {} on tx {}'.format(tx_id, tx))
        self.logger.info("status: {}".format(res.get('status')))
        return res.get('status') == 'completed', res.get('params', {}).get('progress', 0)  # noqa

    def resend_funds_to_main_card(self, card_id, curr_code):
        main_card_id = self.coin_card_mapper(curr_code)
        address_key = self.address_name_mapper(curr_code)

        card_data = self.api.get_card(card_id)
        main_card = self.api.get_card(main_card_id)
        # prevent unwanted conversions
        # TODO: add logging!
        if curr_code != card_data['currency'] or curr_code != main_card['currency']:  # noqa
            return {'success': False, 'retry': False}
        address_to = main_card['address'][address_key]
        amount_to = card_data['balance']
        if Decimal(amount_to) == 0:
            return {'success': False, 'retry': True}
        currency = Currency.objects.get(code=curr_code)
        tx_id, success = self.release_coins(currency, address_to, amount_to,
                                            card=card_id)
        retry = not success
        return {'success': success, 'retry': retry, 'tx_id': tx_id}

    def get_card_validity(self, wallet):
        resp = self.api.get_card(wallet.card_id)
        if resp.get('message') == 'Not Found':
            return False
        return True

    def retry(self, tx):
        tx_id_api = tx.tx_id_api
        if not tx_id_api:
            return {'success': False, 'retry': False}
        card_id = self.coin_card_mapper(tx.currency.code)
        self.logger.info('Retry tx release execute tx_api_id: {}'.format(
            tx_id_api))
        res = self.api.execute_txn(card_id, tx_id_api)
        success = res.get('code') != 'validation_failed'
        retry = not success
        if success:
            tx.is_verified = True
            tx.save()
        return {'success': success, 'retry': retry}

    def get_balance(self, currency):
        card_id = self.coin_card_mapper(currency.code)
        card_data = self.api.get_card(card_id)
        balance = Decimal(str(card_data.get('balance')))
        available = Decimal(str(card_data.get('available')))
        pending = balance - available
        account_data = {
            'balance': balance,
            'available': available,
            'pending': pending
        }
        return account_data
