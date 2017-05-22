from __future__ import absolute_import
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q

from core.models import Transaction
from orders.models import Order
from decimal import Decimal
from nexchange.utils import get_nexchange_logger


class BaseTransactionImporter:
    def __init__(self):
        self.transactions = None
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )

    def get_orders(self, tx):
        sell_query = Q(
            exchange=False,
            order_type=Order.SELL,
            amount_base=Decimal(str(tx['amount'])),
            pair__base=tx['currency'],
            status=Order.INITIAL,
            user=tx['address_to'].user
        )
        buy_exchange_query = Q(
            exchange=True,
            order_type=Order.BUY,
            amount_quote=Decimal(str(tx['amount'])),
            pair__quote=tx['currency'],
            status=Order.INITIAL,
            user=tx['address_to'].user
        )
        sell_exchange_query = Q(
            exchange=True,
            order_type=Order.SELL,
            amount_base=Decimal(str(tx['amount'])),
            pair__base=tx['currency'],
            status=Order.INITIAL,
            user=tx['address_to'].user
        )
        orders = Order.objects.filter(
            sell_query | buy_exchange_query | sell_exchange_query
        )
        return orders

    def get_or_create_tx(self, tx):
        existing_transaction = None
        try:
            if tx['tx_id']:
                query = (
                    Q(tx_id=tx['tx_id']) |
                    Q(tx_id_api=tx['tx_id_api'])
                )
            else:
                query = Q(tx_id_api=tx['tx_id_api'])
            existing_transaction = Transaction.objects.get(
                query
            )
        except MultipleObjectsReturned as e:
            self.logger.error('more than one same transactions exists in DB {}'
                              .format(tx))
            raise e
        except Transaction.DoesNotExist as e:
            self.logger.info('{} transaction not found in DB, creating new...'
                             .format(tx))

        if not existing_transaction:
            self.create_tx(tx)
        else:
            self.logger.info('Transaction with ID {} already exists'.format(
                tx['tx_id'])
            )
            self.api.revert_tx_mapper()

    def create_tx(self, tx_data):
        orders = self.get_orders(tx_data)
        if len(orders) == 1:
            order = orders[0]

            transaction = Transaction(**tx_data)
            transaction.order = order
            transaction.save()
            self.logger.info('New transaction created {}'
                             .format(transaction.__dict__))
            order.status = Order.PAID_UNCONFIRMED
            order.save()
            self.logger.info('Order {} is marked as PAID_UNCONFIRMED'
                             .format(order.__dict__))
        elif len(orders) == 0:
            self.logger.info(
                'Transaction is not created: no orders for transaction '
                '{} found'.format(tx_data))
        elif len(orders) > 1:
            self.logger.info(
                'Transaction is not created: more then 1 order {} found'
                ' for transaction {}'.format(orders, tx_data))

    def import_income_transactions(self):
        # Note: this will only work if node and currency
        # are one to one
        for node in self.api.related_nodes:
            total_txs, txs = self.api.get_txs(node)
            for tx in txs:
                self.get_or_create_tx(tx)
