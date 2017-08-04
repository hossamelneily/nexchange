# flake8: noqa
from .tasks.generate_wallets import renew_cards_reserve
from .tasks.monitor_wallets import update_pending_transactions
from .tasks.monitor_wallets import import_transaction_deposit_crypto
from .tasks.generic.tx_importer.uphold import UpholdTransactionImporter
from .tasks.generic.tx_importer.scrypt import ScryptTransactionImporter
from django.conf import settings
from celery import shared_task
from accounts.tasks.generic.addressreserve_monitor.uphold import \
    UpholdReserveMonitor


uphold_reserve_monitor = UpholdReserveMonitor()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def renew_cards_reserve_invoke():
    return renew_cards_reserve()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def update_pending_transactions_invoke():
    return update_pending_transactions()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_renos_invoke():
    return import_transaction_deposit_crypto(ScryptTransactionImporter)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_uphold_invoke():
    return import_transaction_deposit_crypto(UpholdTransactionImporter)

all_importers = [
    import_transaction_deposit_uphold_invoke,
    import_transaction_deposit_renos_invoke
]


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_crypto_invoke():
    for importer in all_importers:
        importer.apply_async()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_cards_uphold_invoke():
    uphold_reserve_monitor.check_cards()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_cards_balances_uphold_invoke():
    uphold_reserve_monitor.client.check_cards_balances()

