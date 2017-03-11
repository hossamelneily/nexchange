from __future__ import absolute_import
from django.core.exceptions import MultipleObjectsReturned

from core.models import Transaction, Currency
from orders.models import Order
from nexchange.utils import check_address_blockchain
from decimal import Decimal
from django.conf import settings
import logging


class BlockchainTransactionImporter:
    def __init__(self, address, *args, **kwargs):
        self.name = 'Blockchain Transactions'
        self.address = address
        self.min_confirmations = address.currency.min_confirmations if \
            address.currency else settings.MIN_REQUIRED_CONFIRMATIONS
        self.transactions = None
        self.data = None
        self.logger = logging.getLogger(
            self.__class__.__name__
        )

    def get_transactions(self):
        self.transactions = check_address_blockchain(
            self.address
        )

    def transactions_iterator(self):
        if 'txs' in self.transactions:
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
                amount_base=Decimal(str(self.data['amount'])),
                pair__base=self.address.currency,
                status=Order.INITIAL
            )
            if len(orders) == 1:
                order = orders[0]
                transaction = Transaction.objects.create(
                    tx_id=self.data['tx_id'],
                    address_to=self.address,
                    order=orders[0],
                    confirmations=int(self.data['confirmations'])
                )
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
