from orders.tasks.order_release import sell_order_release
from .tasks.generic.buy_order_release import BuyOrderReleaseByRule,\
    BuyOrderReleaseByWallet, BuyOrderReleaseByReference
from .tasks.generic.exchange_order_release import ExchangeOrderRelease
from django.conf import settings
from celery import shared_task
from payments.models import Payment
from orders.models import Order
from core.models import Transaction
from .decorators import get_task


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=BuyOrderReleaseByReference, key='payment__in')
def buy_order_release_by_reference_invoke(payment_id, task=None):
    task.run(payment_id)

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=BuyOrderReleaseByRule, key='payment__in')
def buy_order_release_by_rule_invoke(payment_id, task=None):
    task.run(payment_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=BuyOrderReleaseByWallet, key='payment__in')
def buy_order_release_by_wallet_invoke(payment_id, task=None):
    task.run(payment_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def buy_order_release_reference_periodic():
    for payment in Payment.objects.filter(
        is_success=True,
        is_redeemed=False
    ):
        buy_order_release_by_reference_invoke.apply_async([payment])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def sell_order_release_invoke():
    return sell_order_release()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ExchangeOrderRelease, key='transactions__in')
def exchange_order_release_invoke(transaction_id, task=None):
    task.run(transaction_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def exchange_order_release_periodic():
    txs = Transaction.objects.filter(
        order__exchange=True, order__status=Order.PAID,
        order__withdraw_address__isnull=False
    )
    for tx in txs:
        exchange_order_release_invoke.apply_async([tx.pk])
