from orders.tasks.order_release import sell_order_release
from .tasks.generic.buy_order_release import BuyOrderReleaseByReference, \
    BuyOrderReleaseByWallet, BuyOrderReleaseByRule
from orders.tasks.generic.exchange_order_release import ExchangeOrderRelease
from django.conf import settings
from celery import shared_task
from payments.models import Payment
from orders.models import Order
from core.models import Transaction


release_by_wallet = BuyOrderReleaseByWallet()
release_by_ref = BuyOrderReleaseByReference()
release_by_rule = BuyOrderReleaseByRule()
exchange_order_release = ExchangeOrderRelease()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def buy_order_release_by_reference_invoke(payment_id):
    release_by_ref.run(payment_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def buy_order_release_by_rule_invoke(payment_id):
    release_by_rule.run(payment_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def buy_order_release_by_wallet_invoke(payment_id):
    release_by_wallet.run(payment_id)


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
def exchange_order_release_invoke(transaction_id):
    exchange_order_release.run(transaction_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def exchange_order_release_periodic():
    txs = Transaction.objects.filter(
        order__exchange=True, order__status=Order.PAID,
        order__withdraw_address__isnull=False
    )
    for tx in txs:
        exchange_order_release_invoke.apply_async([tx.pk])
