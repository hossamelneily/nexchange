from django.conf import settings
from celery import shared_task

from .tasks.generic.eth_balance_checker import EthBalanceChecker
from .tasks.generic.address_turnover_checker import AddressTurnoverChecker
from .tasks.generic.related_turnover_checker import RelatedTurnoverChecker
from .tasks.generic.token_balance_checker import TokenBalanceChecker
from .tasks.generic.category_checker import CategoryChecker

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


@shared_task(time_limit=settings.LONG_TASKS_TIME_LIMIT)
def subscription_token_balances_check_invoke(subscription_id):
    task = TokenBalanceChecker()
    task.run(subscription_id)


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def subscription_category_check_invoke(subscription_id):
    task = CategoryChecker()
    task.run(subscription_id)


subscription_checkers = [
    subscription_eth_balance_check_invoke,
    subscription_address_turnover_check_invoke,
    subscription_related_turnover_check_invoke,
    subscription_token_balances_check_invoke,
    subscription_category_check_invoke
]
total_time_limit = sum([t.time_limit for t in subscription_checkers])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def subscription_checker_periodic():
    subs = Subscription.objects.exclude(
        sending_address=None
    ).exclude(sending_address='').order_by('-id')
    for i, sub in enumerate(subs):
        sub_id = sub.pk
        base_delay = i * total_time_limit
        additional_delay = 0
        for task in subscription_checkers:
            task.apply_async(
                [sub_id],
                countdown=base_delay + additional_delay
            )
            additional_delay += task.time_limit
