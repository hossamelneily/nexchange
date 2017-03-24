from __future__ import absolute_import
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q

from core.models import Transaction, Currency
from orders.models import Order
from nexchange.utils import get_uphold_card_transactions, api
from decimal import Decimal
import logging


class UpholdTransactionImporter:
    def __init__(self, card, addr, *args, **kwargs):
        self.name = 'Uphold Transactions'
        self.card = card
        self.address = addr
        self.transactions = None
        self.data = None
        self.logger = logging.getLogger(
            self.__class__.__name__
        )

    def get_transactions(self):
        card_id = self.card.card_id
        existing_tx_ids = [tx.tx_id_api for tx in Transaction.objects.all()]
        txs = get_uphold_card_transactions(
            card_id, trans_type='incoming'
        )
        self.transactions = [
            tx for tx in txs if tx['id'] not in existing_tx_ids
        ]

    def transactions_iterator(self):
        for trans in self.transactions:
            yield trans

    def parse_data(self, trans):
        try:
            _currency = Currency.objects.get(
                code=trans['destination']['currency']
            )
            tx_id_api = trans['id']
            res = api.get_reserve_transaction(tx_id_api)
            tx_id = res.get('params', {}).get('txid', None)
            self.data = {
                # required
                'currency': _currency,
                'amount': trans['destination']['amount'],
                'time_utc': trans['createdAt'],
                'tx_id_api': tx_id_api,
                'tx_id': tx_id
            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))

    def get_orders(self):
        sell_query = Q(
            exchange=False,
            order_type=Order.SELL,
            amount_base=Decimal(str(self.data['amount'])),
            pair__base=self.data['currency'],
            status=Order.INITIAL,
            user=self.card.user
        )
        buy_exchange_query = Q(
            exchange=True,
            order_type=Order.BUY,
            amount_quote=Decimal(str(self.data['amount'])),
            pair__quote=self.data['currency'],
            status=Order.INITIAL,
            user=self.card.user
        )
        sell_exchange_query = Q(
            exchange=True,
            order_type=Order.SELL,
            amount_base=Decimal(str(self.data['amount'])),
            pair__base=self.data['currency'],
            status=Order.INITIAL,
            user=self.card.user
        )
        orders = Order.objects.filter(
            sell_query | buy_exchange_query | sell_exchange_query
        )
        return orders

    def create_transaction(self):
        existing_transaction = None
        try:
            if self.data['tx_id'] is not None:
                query = (
                    Q(tx_id=self.data['tx_id']) |
                    Q(tx_id_api=self.data['tx_id_api'])
                )
            else:
                query = Q(tx_id_api=self.data['tx_id_api'])
            existing_transaction = Transaction.objects.get(
                query
            )
        except MultipleObjectsReturned:
            self.logger.error('more than one same transactions exists in DB {}'
                              .format(self.data))
        except Transaction.DoesNotExist:
            self.logger.info('{} transaction not found in DB, creating new...'
                             .format(self.data))

        if existing_transaction is None:
            orders = self.get_orders()
            if len(orders) == 1:
                order = orders[0]
                txs_data = {
                    'tx_id_api': self.data['tx_id_api'],
                    'address_to': self.address,
                    'order': order
                }
                if self.data['tx_id'] is not None:
                    txs_data.update({
                        'tx_id': self.data['tx_id']
                    })
                transaction = Transaction(**txs_data)
                transaction.save()
                self.logger.info('...new transaction created {}'
                                 .format(transaction.__dict__))
                order.status = Order.PAID_UNCONFIRMED
                order.save()
                self.logger.info('Order {} is marked as PAID_UNCONFIRMED'
                                 .format(order.__dict__))
            elif len(orders) == 0:
                self.logger.info(
                    '...Transaction is not created: no orders for transaction '
                    '{} found'.format(self.data))
            elif len(orders) > 1:
                self.logger.info(
                    '...Transaction is not created: more then 1 order {} found'
                    ' for transaction {}'.format(orders, self.data))
        else:
            self.logger.info('Transaction with ID {} already exists'.format(
                self.data['tx_id'])
            )

    def import_income_transactions(self):
        self.get_transactions()

        for trans in self.transactions_iterator():
            try:
                self.parse_data(trans)
            except ValueError:
                continue
            except KeyError:
                continue
            self.create_transaction()
