# flake8: noqa
from accounts.tasks.generate_wallets import renew_cards_reserve
from accounts.tasks.monitor_wallets import update_pending_transactions
from .tasks.monitor_wallets import import_transaction_deposit_btc
from django.conf import settings
from celery import shared_task


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def renew_cards_reserve_invoke():
    return renew_cards_reserve()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def update_pending_transactions_invoke():
    return update_pending_transactions()

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_btc_invoke():
    return import_transaction_deposit_btc()
