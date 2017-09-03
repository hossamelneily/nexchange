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
from nexchange.utils import check_transaction_blockchain
from django.core.exceptions import ValidationError


def mark_card_for_balance_check(tr, logger, next_tasks):
    order = tr.order
    card = tr.address_to.reserve

    if card:
        card.need_balance_check = True
        card.save()
    if not order.exchange:
        next_tasks.add((sell_order_release_invoke, None,))
    else:
        next_tasks.add((exchange_order_release_invoke, tr.pk,))

    if settings.DEBUG:
        logger.info('Transaction {} is completed'.format(tr.tx_id))


def check_uphold_txn_status_with_blockchain(tr, tx_completed,
                                            num_confirmations, logger):
    is_uphold_coin = tr.address_to.currency.code in settings.API1_COINS
    if not is_uphold_coin:
        return tx_completed, num_confirmations
    if num_confirmations is None or num_confirmations < 2:
        logger.info('UPHOLD did not return confirmations count,'
                    ' falling back to 3rd party API')
    elif tx_completed:
        return tx_completed, num_confirmations
    num_confirmations = check_transaction_blockchain(tr)
    # FIXME: different return types on check_transaction_blockchain
    if isinstance(num_confirmations, tuple):
        num_confirmations = num_confirmations[1]
    tx_completed = num_confirmations >= tr.currency.min_confirmations
    if tx_completed:
        logger.info('UPHOLD did not return status="completed" when it is '
                    'more when minimal amount of confirmations on '
                    'blockchain response')
    return tx_completed, num_confirmations


def _update_pending_transaction(tr, logger, next_tasks=None):
    currency_to = tr.address_to.currency
    api = ApiClientFactory.get_api_client(currency_to.wallet)
    order = tr.order

    logger.info(
        'Look-up transaction with txid api {} '.format(tr.tx_id_api)
    )
    tx_completed, num_confirmations = api.check_tx(tr, currency_to)

    # Uphold is shit, fall back to external source to confirm tx
    # num_confirmations < 2 is to fix the uphold bug that returns 1 for any amount
    # of confirmations
    # TODO: remove, if and when Uphold API gets better
    tx_completed, num_confirmations = check_uphold_txn_status_with_blockchain(
        tr, tx_completed, num_confirmations, logger)

    tr.confirmations = num_confirmations
    with transaction.atomic():
        withdrawal_completed = tr.address_to.type == Address.WITHDRAW and \
            tx_completed
        deposit_completed = tr.address_to.type == Address.DEPOSIT and \
            tx_completed

        if withdrawal_completed:
            tr.is_completed = True
            tr.is_verified = True
            order.status = Order.COMPLETED

        if deposit_completed:
            tr.is_completed = True
            tr.is_verified = True
            order.status = Order.PAID
        tr.save()
        order.save()

        # TODO: change me to add_next_task()
        if deposit_completed:
            if order.exchange:
                next_tasks.add((exchange_order_release_invoke, tr.pk,))
            else:
                next_tasks.add((sell_order_release_invoke, None,))

            # TODO: implement me as next task
            mark_card_for_balance_check(tr, logger, next_tasks)


def update_pending_transactions():
    logger = get_nexchange_logger(__name__, True, True)
    next_tasks = set()
    for tr in Transaction.objects. \
            filter(Q(is_completed=False) | Q(is_verified=False), flagged=False):  # noqa
        try:
            _update_pending_transaction(tr, logger, next_tasks=next_tasks)
        except ValidationError as e:
            logger.info(e)
        except Exception as e:
            logger.info(e)
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
