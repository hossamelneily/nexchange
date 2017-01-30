from __future__ import absolute_import
from django.core.exceptions import MultipleObjectsReturned

from core.models import Transaction, Currency
from orders.models import Order
from nexchange.utils import check_address_blockchain
from decimal import Decimal
import logging


class BlockchainTransactionImporter:

    def __init__(self, address, min_confirmations=3, *args, **kwargs):
        self.name = 'Blockchain Transactions'
        self.address = address
        self.confirmations = min_confirmations

        self.logger = logging.getLogger(
            self.__class__.__name__
        )

    def get_transactions(self):
        self.transactions = check_address_blockchain(
            self.address, confirmations=self.confirmations
        )

    def transactions_iterator(self):
        for trans in self.transactions['txs']:
            yield trans

    def parse_data(self, trans):
        try:
            self.data = {
                # required
                'currency': (self.address.currency or
                             Currency.objects.get(code='BTC')),
                'amount': trans['amount'],
                'confirmations': trans['confirmations'],
                'tx_id': trans['tx'],
                'time_utc': trans['time_utc']
            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))

    def create_transaction(self):
        existing_transaction = None
        try:
            existing_transaction = Transaction.objects.get(
                tx_id=self.data['tx_id']
            )
        except MultipleObjectsReturned:
            self.logger.error('more than one same transactions exists in DB {}'
                              .format(self.data))
        except Transaction.DoesNotExist:
            self.logger.info('{} transaction not found in DB, creating new...'
                             .format(self.data))

        if existing_transaction is None:
            orders = Order.objects.filter(
                order_type=Order.SELL,
                amount_btc=Decimal(str(self.data['amount'])),
                is_completed=False,
                is_paid=False
            )
            if len(orders) == 1:
                order = orders[0]
                transaction = Transaction.objects.create(
                    tx_id=self.data['tx_id'],
                    address_to=self.address,
                    order=orders[0]
                )
                transaction.save()
                self.logger.info('...new transaction created {}'
                                 .format(transaction.__dict__))
                order.is_paid = True
                order.save()
                self.logger.info('Order {} is marked as paid (is_paid=True)'
                                 .format(order.__dict__))
            elif len(orders) == 0:
                self.logger.info(
                    '...Transaction is not created: no orders for transaction '
                    '{} found'.format(self.data))
            elif len(orders) > 1:
                self.logger.info(
                    '...Transaction is not created: more then 1 order {} found'
                    ' for transaction {}'.format(orders, self.data))

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
