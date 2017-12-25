# flake8: noqa
from .tasks.generate_wallets import renew_cards_reserve
from .tasks.monitor_wallets import update_pending_transactions
from .tasks.monitor_wallets import import_transaction_deposit_crypto
from .tasks.generic.tx_importer.uphold import UpholdTransactionImporter
from .tasks.generic.tx_importer.uphold_blockchain import \
    UpholdBlockchainTransactionImporter
from .tasks.generic.tx_importer.scrypt import ScryptTransactionImporter, \
    EthashTransactionImporter, Blake2TransactionImporter
from django.conf import settings
from celery import shared_task
from core.models import AddressReserve
from core.models import Transaction
from accounts.decoratos import get_task
from accounts.tasks.generic.addressreserve_monitor.base import ReserveMonitor
from nexchange.celery import app


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
def import_transaction_deposit_ethash_invoke():
    return import_transaction_deposit_crypto(EthashTransactionImporter)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_blake2_invoke():
    return import_transaction_deposit_crypto(Blake2TransactionImporter)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_uphold_invoke():
    return import_transaction_deposit_crypto(UpholdTransactionImporter)

all_importers = [
    import_transaction_deposit_scrypt_invoke,
    import_transaction_deposit_ethash_invoke,
    import_transaction_deposit_blake2_invoke
]


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_crypto_invoke():
    for importer in all_importers:
        importer.apply_async()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveMonitor, key='pk__in')
def check_card_balance_invoke(card_id, task=None):
    res = task.client.check_card_balance(card_id)
    return res

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveMonitor, key='pk__in')
def send_gas_to_card_invoke(card_id, task=None):
    res = task.client.add_gas_to_card(card_id)
    return res

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def send_gas_to_transaction_card_invoke(tx_id):
    tx = Transaction.objects.get(pk=tx_id)
    if tx.order.pair.quote.is_token:
        card = tx.address_to.reserve
        return send_gas_to_card_invoke.apply([card.pk])


@app.task(bind=True)
def check_transaction_card_balance_invoke(self, tx_id):
    tx = Transaction.objects.get(pk=tx_id)
    card = tx.address_to.reserve
    if card:
        task_info = check_card_balance_invoke.apply([card.pk])
        res = task_info.result
        if res.get('retry'):
            self.retry(countdown=settings.CARD_CHECK_TIME,
                       max_retries=settings.RETRY_CARD_CHECK_MAX_RETRIES)


@shared_task(time_limit=settings.TRANSACTION_IMPORT_TIME_LIMIT)
def import_transaction_deposit_uphold_blockchain_invoke():
    return import_transaction_deposit_crypto(UpholdBlockchainTransactionImporter)
