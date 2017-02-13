from __future__ import absolute_import
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from core.models import Transaction, Address
from orders.models import Order
from nexchange.utils import check_transaction_blockchain, \
    check_transaction_uphold, send_email, send_sms
from accounts.utils import BlockchainTransactionImporter
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
            order.state = Order.COMPLETED
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


def import_transaction_deposit_btc():
    address = Address.objects.filter(
        Q(currency__code='BTC') | Q(currency=None),
        type=Address.DEPOSIT
    )
    for add in address:
        importer = BlockchainTransactionImporter(
            add, min_confirmations=settings.MIN_REQUIRED_CONFIRMATIONS
        )
        importer.import_income_transactions()
