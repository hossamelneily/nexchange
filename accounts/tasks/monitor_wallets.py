from __future__ import absolute_import
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import MultipleObjectsReturned

from core.models import Transaction, Address, Currency
from orders.models import Order
from nexchange.utils import check_transaction_blockchain, \
    check_transaction_uphold, send_email, send_sms, check_address_blockchain
from decimal import Decimal
import logging


def update_pending_transactions():
    for tr in Transaction.objects.\
            filter(Q(is_completed=False) | Q(is_verified=False)):
        order = tr.order
        profile = order.user.profile
        logging.info(
            'Look-up transaction with txid api {} '.format(tr.tx_id_api))
        if check_transaction_uphold(tr):
            tr.is_completed = True
            tr.save()
            order.is_completed = True
            order.save()

        if check_transaction_blockchain(tr):
            tr.is_verified = True
            tr.save()

            title = _('Nexchange: Order released')
            msg = _('Your order {}:  is released'). \
                format(tr.order.o.unique_reference)

            if profile.notify_by_phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    logging.info(str(sms_result))

            if profile.notify_by_email:
                email = send_email(tr.order.user.email, title, msg)
                email.send()

            if settings.DEBUG:
                logging.info('Transaction {} is completed'.format(tr.tx_id))


class BlockchainTransactionChecker:

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
                'currency': self.address.currency or Currency.get(code='BTC'),
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

    def run(self):
        self.get_transactions()

        for trans in self.transactions_iterator():
            try:
                self.parse_data(trans)
            except ValueError:
                continue
            except KeyError:
                continue
            self.create_transaction()


@shared_task
def import_transactionDeposit_btc():
    address = Address.objects.filter(type=Address.DEPOSIT)
    for add in address:
        importer = BlockchainTransactionChecker(
            add, min_confirmations=settings.MIN_REQUIRED_CONFIRMATIONS
        )
        importer.run()
