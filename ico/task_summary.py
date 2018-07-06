from django.conf import settings
from celery import shared_task

from .tasks.generic.eth_balance_checker import EthBalanceChecker
from .tasks.generic.address_turnover_checker import AddressTurnoverChecker
from .tasks.generic.related_turnover_checker import RelatedTurnoverChecker
from .tasks.generic.token_balance_checker import TokenBalanceChecker
from .models import Subscription


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def subscription_eth_balance_check_invoke(subscription_id):
    task = EthBalanceChecker()
    task.run(subscription_id)


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def subscription_address_turnover_check_invoke(subscription_id):
    task = AddressTurnoverChecker()
    task.run(subscription_id)


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def subscription_related_turnover_check_invoke(subscription_id):
    task = RelatedTurnoverChecker()
    task.run(subscription_id)


@shared_task(time_limit=settings.MODERATE_TASKS_TIME_LIMIT)
def subscription_token_balances_check_invoke(subscription_id):
    task = TokenBalanceChecker()
    task.run(subscription_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def subscription_checker_periodic():
    subs = Subscription.objects.exclude(
        sending_address=None
    ).exclude(sending_address='')
    for sub in subs:
        sub_id = sub.pk
        subscription_eth_balance_check_invoke.apply_async([sub_id])
        subscription_address_turnover_check_invoke.apply_async(
            [sub_id],
            countdown=settings.FAST_TASKS_TIME_LIMIT
        )
        subscription_related_turnover_check_invoke.apply_async(
            [sub_id],
            countdown=settings.FAST_TASKS_TIME_LIMIT * 2
        )
        subscription_token_balances_check_invoke.apply_async(
            [sub_id],
            countdown=settings.FAST_TASKS_TIME_LIMIT * 3
        )
