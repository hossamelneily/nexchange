from accounts.tasks.generic.tx_importer.base import BaseTransactionImporter
from orders.models import Order
from django.conf import settings
from nexchange.utils import check_address_transaction_ids_blockchain
from core.models import Transaction
from django.core.exceptions import MultipleObjectsReturned


class UpholdBlockchainTransactionImporter(BaseTransactionImporter):

    def get_orders(self):
        orders = Order.objects.filter(
            status=Order.INITIAL, pair__quote__code__in=settings.API1_COINS)
        return orders

    def get_or_create_tx(self, tx):
        existing_transaction = None
        try:
            existing_transaction = Transaction.objects.get(tx_id=tx['tx_id'])
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
            # self.api.revert_tx_mapper()

    def create_tx(self, tx_data):
        if self.order.status != Order.INITIAL:
            return

        transaction = Transaction(**tx_data)
        transaction.type = transaction.DEPOSIT
        transaction.save()
        self.logger.info('New transaction created {}'
                         .format(transaction.__dict__))
        self.order.status = Order.PAID_UNCONFIRMED
        self.order.save()
        self.logger.info('Order {} is marked as PAID_UNCONFIRMED'
                         .format(self.order.__dict__))

    def import_income_transactions(self):
        orders = self.get_orders()
        for order in orders:
            self.order = order
            address = order.deposit_address
            res = check_address_transaction_ids_blockchain(address)
            for tx in res[1]:
                if self.order.amount_quote != tx['amount']:
                    continue
                tx.update({
                    'order': self.order,
                    'address_to': address,
                    'currency': order.pair.quote})
                self.get_or_create_tx(tx)
                if self.order.status != Order.INITIAL:
                    continue
