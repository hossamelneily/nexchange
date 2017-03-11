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
from django.db import transaction


def update_pending_transactions():
    logger = get_nexchange_logger(__name__, True, True)
    next_tasks = set()
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

            with transaction.atomic():
                tr.is_completed = True
                tr.is_verified = True
                tr.save()
                order.status = Order.PAID
                order.save()
                next_tasks.add(sell_order_release_invoke)

            # trigger release
            title = _('Nexchange: Order released')
            msg = _('Your order {}:  is released. '
                    '\n {} {} were sent to {} {} {}'). \
                format(tr.order.unique_reference,
                       tr.order.amount_quote,
                       tr.order.pair.quote.code,
                       tr.order.payment_preference.payment_method.name,
                       tr.order.payment_preference.identifier,
                       '('+tr.order.payment_preference.secondary_identifier+')'# noqa
                       if tr.order.payment_preference.secondary_identifier
                       else '')

            if profile.notify_by_phone and profile.phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    logger.info(str(sms_result))

            if profile.notify_by_email and order.user.email:
                email = send_email(tr.order.user.email, title, msg)
                email.send()

            if settings.DEBUG:
                logger.info('Transaction {} is completed'.format(tr.tx_id))

    for task in next_tasks:
        res = task.apply()
        if res.state != 'SUCCESS':
            logger.error('Task release_sell_order returned '
                         'error traceback: {}'.format(res.traceback))


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
