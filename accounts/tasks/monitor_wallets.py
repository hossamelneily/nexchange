from __future__ import absolute_import
from django.conf import settings
from django.db.models import Q

from core.models import Transaction, Address
from orders.models import Order
from nexchange.utils import get_nexchange_logger
from orders.task_summary import exchange_order_release_invoke
from django.db import transaction
from nexchange.api_clients.factory import ApiClientFactory
from nexchange.utils import check_transaction_blockchain
from django.core.exceptions import ValidationError
from nexchange.celery import app


CHECK_CARD_BALANCE_TASK = 'accounts.task_summary.' \
                          'check_transaction_card_balance_invoke'


def check_uphold_txn_status_with_blockchain(tx, tx_completed,
                                            num_confirmations, logger):
    is_uphold_coin = tx.address_to.currency.code in settings.API1_COINS
    if not is_uphold_coin:
        return tx_completed, num_confirmations
    # FIXME: tx_id_api is not updated with Uphold transaction importer.
    # Check transaction Mapper, do real test on localhost
    # if tx.tx_id_api is None:
    #     return tx_completed, num_confirmations
    if num_confirmations is None or num_confirmations < 2:
        logger.info('UPHOLD did not return confirmations count,'
                    ' falling back to 3rd party API')
    elif tx_completed:
        return tx_completed, num_confirmations
    num_confirmations = check_transaction_blockchain(tx)
    # FIXME: different return types on check_transaction_blockchain
    if isinstance(num_confirmations, tuple):
        num_confirmations = num_confirmations[1]
    tx_completed = num_confirmations >= tx.currency.min_confirmations
    if tx_completed:
        logger.info('UPHOLD did not return status="completed" when it is '
                    'more when minimal amount of confirmations on '
                    'blockchain response')
    return tx_completed, num_confirmations


def _update_pending_transaction(tx, logger, next_tasks=None):
    currency_to = tx.address_to.currency
    api = ApiClientFactory.get_api_client(currency_to.wallet)
    order = tx.order

    logger.info(
        'Look-up transaction with txid api {} '.format(tx.tx_id_api)
    )
    tx_completed, num_confirmations = api.check_tx(tx, currency_to)

    # Uphold is shit, fall back to external source to confirm tx
    # num_confirmations < 2 is to fix the uphold bug that returns 1 for any amount
    # of confirmations
    # TODO: remove, if and when Uphold API gets better
    tx_completed, num_confirmations = check_uphold_txn_status_with_blockchain(
        tx, tx_completed, num_confirmations, logger)

    tx.confirmations = num_confirmations
    with transaction.atomic():
        withdrawal_completed = tx.address_to.type == Address.WITHDRAW and \
            tx_completed and order.status != Order.COMPLETED
        deposit_completed = tx.address_to.type == Address.DEPOSIT and \
            tx_completed and order.status not in Order.IN_PAID

        if withdrawal_completed:
            order.complete(tx)

        if deposit_completed:
            confirm_res = order.confirm_deposit(tx)
            order.refresh_from_db()
            confirm_status_ok = confirm_res.get('status') == 'OK'

            # TODO: change me to add_next_task()
            if confirm_status_ok and order.status == Order.PAID:
                # TODO: implement me as next task
                next_tasks.add((exchange_order_release_invoke, tx.pk,))
                app.send_task(CHECK_CARD_BALANCE_TASK, [tx.pk],
                              countdown=settings.CARD_CHECK_TIME)


def update_pending_transactions():
    logger = get_nexchange_logger(__name__, True, True)
    next_tasks = set()
    for tx in Transaction.objects. \
            filter(Q(is_completed=False) | Q(is_verified=False), flagged=False):  # noqa
        try:
            _update_pending_transaction(tx, logger, next_tasks=next_tasks)
        except ValidationError as e:
            logger.info(e)
        except Exception as e:
            logger.info(e)
    for task, args in next_tasks:
        if args is not None:
            res = task.apply_async([args])
        else:
            res = task.apply_async()
        if res.state != 'SUCCESS':
            logger.error(
                'Task {} returned error traceback: {}'.format(
                    task.name, res.traceback))


def import_transaction_deposit_crypto(Importer):
    importer = Importer()
    importer.import_income_transactions()
