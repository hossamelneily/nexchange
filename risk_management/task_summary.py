from django.conf import settings
from celery import shared_task

from risk_management.decorators import get_task
from risk_management.tasks.generic.account_balance_checker import \
    AccountBalanceChecker
from risk_management.tasks.generic.reserve_balance_checker import \
    ReserveBalanceChecker
from risk_management.tasks.generic.reserve_balance_maintainer import \
    ReserveBalanceMaintainer
from risk_management.tasks.generic.main_account_filler import MainAccountFiller
from risk_management.models import Reserve


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=AccountBalanceChecker)
def account_balance_checker_invoke(account_id, task=None):
    task.run(account_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveBalanceChecker)
def reserve_balance_checker_invoke(reserve_id, task=None):
    task.run(reserve_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def reserves_balance_checker_periodic():
    reserves = Reserve.objects.all()
    for reserve in reserves:
        reserve_balance_checker_invoke.apply([reserve.pk])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveBalanceMaintainer)
def reserve_balance_maintainer_invoke(reserve_id, task=None):
    task.run(reserve_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def main_account_filler_invoke(account_id, amount):
    task = MainAccountFiller()
    task.run(account_id, amount)
