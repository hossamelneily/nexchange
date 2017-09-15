# flake8: noqa
from .tasks.generate_wallets import renew_cards_reserve
from .tasks.monitor_wallets import update_pending_transactions
from .tasks.monitor_wallets import import_transaction_deposit_crypto
from .tasks.generic.tx_importer.uphold import UpholdTransactionImporter
from .tasks.generic.tx_importer.uphold_blockchain import \
    UpholdBlockchainTransactionImporter
from .tasks.generic.tx_importer.scrypt import ScryptTransactionImporter
from django.conf import settings
from celery import shared_task
from core.models import AddressReserve
from core.models import Transaction
from accounts.decoratos import get_task
from accounts.tasks.generic.addressreserve_monitor.base import ReserveMonitor


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def renew_cards_reserve_invoke():
    return renew_cards_reserve()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def update_pending_transactions_invoke():
    return update_pending_transactions()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_scrypt_invoke():
    return import_transaction_deposit_crypto(ScryptTransactionImporter)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_uphold_invoke():
    return import_transaction_deposit_crypto(UpholdTransactionImporter)

all_importers = [
    import_transaction_deposit_uphold_invoke,
    import_transaction_deposit_scrypt_invoke
]


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_crypto_invoke():
    for importer in all_importers:
        importer.apply_async()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveMonitor, key='pk__in')
def check_cards_balances_invoke(card_id, task=None):
    task.client.check_cards_balances(card_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_transaction_card_balance_invoke(tx_id):
    tx = Transaction.objects.get(pk=tx_id)
    card = tx.address_to.reserve
    if card:
        check_cards_balances_invoke.apply_async([card.pk])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_cards_balances_uphold_periodic():
    wallet = 'api1'
    card = AddressReserve.objects.filter(
        user__isnull=False, need_balance_check=True, disabled=False,
        currency__wallet=wallet).first()
    if card is None:
        return
    check_cards_balances_invoke.apply([card.pk])
    card.need_balance_check = False
    card.save()


@shared_task(time_limit=settings.TRANSACTION_IMPORT_TIME_LIMIT)
def import_transaction_deposit_uphold_blockchain_invoke():
    return import_transaction_deposit_crypto(UpholdBlockchainTransactionImporter)
