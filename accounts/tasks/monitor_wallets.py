from __future__ import absolute_import
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from core.models import Transaction, Address
from orders.models import Order
from nexchange.utils import check_transaction_blockchain, \
    check_transaction_uphold, send_email, send_sms
from accounts.utils import BlockchainTransactionImporter
from nexchange.utils import get_nexchange_logger
from orders.task_summary import sell_order_release_invoke


def update_pending_transactions():
    logger = get_nexchange_logger(__name__, True, True)
    for tr in Transaction.objects.\
            filter(Q(is_completed=False) | Q(is_verified=False)):
        order = tr.order
        profile = order.user.profile
        logger.info(
            'Look-up transaction with txid api {} '.format(tr.tx_id_api))
        if tr.address_to.type == Address.WITHDRAW and \
                check_transaction_uphold(tr):
            tr.is_completed = True
            tr.is_verified = True
            tr.save()
            order.status = Order.COMPLETED
            order.save()

        if tr.address_to.type == Address.DEPOSIT and \
                check_transaction_blockchain(tr):
            tr.is_completed = True
            tr.is_verified = True
            tr.save()
            order.status = Order.PAID
            order.save()
            # trigger release
            sell_order_release_invoke.apply_assync()
            title = _('Nexchange: Order released')
            msg = _('Your order {}:  is released'). \
                format(tr.order.o.unique_reference)

            if profile.notify_by_phone and profile.phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    logger.info(str(sms_result))

            if profile.notify_by_email and profile.email:
                email = send_email(tr.order.user.email, title, msg)
                email.send()

            if settings.DEBUG:
                logger.info('Transaction {} is completed'.format(tr.tx_id))


def import_transaction_deposit_btc():
    addresses = Address.objects.filter(
        Q(currency__is_crypto=True) | Q(currency=None),
        type=Address.DEPOSIT
    )
    for addr in addresses:
        importer = BlockchainTransactionImporter(
            addr
        )
        importer.import_income_transactions()
