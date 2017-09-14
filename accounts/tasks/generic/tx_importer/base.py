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
        buy_exchange_query = {
            'exchange': True,
            'order_type': Order.BUY,
            'amount_quote': Decimal(str(tx['amount'])),
            'pair__quote': tx['currency'],
            'status': Order.INITIAL,
            'user': tx['address_to'].user,
            'deposit_address': tx['address_to']
        }
        orders = Order.objects.filter(**buy_exchange_query)
        orders = [order for order in orders if not order.expired]
        return orders

    def get_or_create_tx(self, tx):
        existing_transaction = None
        try:
            if tx['tx_id'] and tx['tx_id_api']:
                query = (
                    Q(tx_id=tx['tx_id']) |
                    Q(tx_id_api=tx['tx_id_api'])
                )
            elif not tx['tx_id'] and tx['tx_id_api']:
                query = Q(tx_id_api=tx['tx_id_api'])
            elif tx['tx_id'] and not tx['tx_id_api']:
                query = Q(tx_id_api=tx['tx_id'])
            else:
                raise ValueError(
                    'Transaction data does not contain any information about '
                    'transaction({}) id(tx_id) or api_id(tx_api_id)'.format(tx)
                )
            existing_transaction = Transaction.objects.get(
                query
            )
        except MultipleObjectsReturned as e:
            self.logger.error('more than one same transactions exists in DB {}'
                              .format(tx))
            raise e
        except Transaction.DoesNotExist:
            self.logger.info('{} transaction not found in DB, creating new...'
                             .format(tx))
        except ValueError as e:
            self.logger.info(e)
            raise e

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

            tx_data.update({
                'order': order,
                'type': Transaction.DEPOSIT
            })

            register_res = order.register_deposit(tx_data)

            if register_res.get('status') == 'OK':
                txn = register_res.get('tx')
                self.logger.info('New transaction created {}'
                                 .format(txn.__dict__))
                self.logger.info('Order {} is marked as PAID_UNCONFIRMED'
                                 .format(order.__dict__))
        elif len(orders) == 0:
            self.logger.info(
                'Transaction is not created: no orders for transaction '
                '{} found'.format(tx_data))
        elif len(orders) > 1:
            self.logger.error(
                'Transaction is not created: more then 1 order {} found'
                ' for transaction {}'.format(orders, tx_data))

    def import_income_transactions(self):
        # Note: this will only work if node and currency
        # are one to one
        for node in self.api.related_nodes:
            total_txs, txs = self.api.get_txs(node)
            for tx in txs:
                if tx['address_to'] is not None:
                    self.get_or_create_tx(tx)
                else:
                    self.logger.info(
                        'Transaction has no address_to: {}'.format(tx))
