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
from risk_management.models import Reserve, PortfolioLog, PNLSheet
from risk_management.tasks.generic.currency_cover import CurrencyCover
from risk_management.tasks.generic.order_cover import OrderCover
from django.utils.timezone import now, timedelta


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=AccountBalanceChecker)
def account_balance_checker_invoke(account_id, task=None):
    task.run(account_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveBalanceChecker)
def reserve_balance_checker_invoke(reserve_id, task=None):
    task.run(reserve_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def currency_reserve_balance_checker_invoke(currency_code):
    reserve = Reserve.objects.get(currency__code=currency_code)
    reserve_balance_checker_invoke.apply([reserve.pk])


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
def main_account_filler_invoke(account_id, amount=None, do_trade=False):
    task = MainAccountFiller()
    task.run(account_id, amount=amount, do_trade=do_trade)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def order_cover_invoke(order_id):
    task = OrderCover()
    cover, send_to_main, amount = task.run(order_id)
    if send_to_main and amount:
        main_account_filler_invoke.apply_async(
            [cover.account.pk, amount],
            countdown=settings.THIRD_PARTY_TRADE_TIME
        )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def currency_cover_invoke(currency_code, amount):
    task = CurrencyCover()
    cover = task.run(currency_code, amount)
    if cover:
        main_account_filler_invoke.apply_async(
            [cover.account.pk, cover.amount_base],
            countdown=settings.THIRD_PARTY_TRADE_TIME
        )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def log_current_assets():
    new_log = PortfolioLog()
    new_log.save()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def calculate_pnls():
    date_from = now() - timedelta(hours=24)
    date_to = now()
    new_sheet = PNLSheet(date_from=date_from, date_to=date_to)
    new_sheet.save()
