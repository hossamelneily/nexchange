from __future__ import absolute_import
from django.conf import settings
from django.db.models import Q

from core.models import Transaction, Address
from orders.models import Order
from nexchange.utils import get_nexchange_logger
from orders.task_summary import (sell_order_release_invoke,
                                 exchange_order_release_invoke)
from django.db import transaction
from nexchange.api_clients.factory import ApiClientFactory


def _update_pending_transaction(tr, logger, next_tasks=None):
    currency_to = tr.address_to.currency
    api = ApiClientFactory.get_api_client(currency_to.wallet)
    order = tr.order

    logger.info(
        'Look-up transaction with txid api {} '.format(tr.tx_id_api))
    if tr.address_to.type == Address.WITHDRAW and \
            api.check_tx(tr, currency_to):
        tr.is_completed = True
        tr.is_verified = True
        tr.save()
        order.status = Order.COMPLETED
        order.save()
        order.notify(tx_id=tr.tx_id)

    if tr.address_to.type == Address.DEPOSIT and \
            api.check_tx(tr, currency_to):

        with transaction.atomic():
            tr.is_completed = True
            tr.is_verified = True
            tr.save()
            order.status = Order.PAID
            order.save()
        card = tr.address_to.reserve
        if card:
            card.need_balance_check = True
            card.save()
        if not order.exchange:
            next_tasks.add((sell_order_release_invoke, None,))
        else:
            next_tasks.add((exchange_order_release_invoke, tr.pk, ))

        order.notify()

        if settings.DEBUG:
            logger.info('Transaction {} is completed'.format(tr.tx_id))


def update_pending_transactions():
    logger = get_nexchange_logger(__name__, True, True)
    next_tasks = set()
    for tr in Transaction.objects. \
            filter(Q(is_completed=False) | Q(is_verified=False)):
        try:
            _update_pending_transaction(tr, logger, next_tasks=next_tasks)
        except Exception as e:
            logger.warning(e)
    for task, args in next_tasks:
        if args is not None:
            res = task.apply([args])
        else:
            res = task.apply()
        if res.state != 'SUCCESS':
            logger.error(
                'Task {} returned error traceback: {}'.format(
                    task.name, res.traceback))


def import_transaction_deposit_crypto(Importer):
    importer = Importer()
    importer.import_income_transactions()
