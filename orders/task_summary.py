from orders.tasks.order_release import sell_order_release
from .tasks.generic.buy_order_release import BuyOrderReleaseByReference, \
    BuyOrderReleaseByWallet, BuyOrderReleaseByRule
from django.conf import settings
from celery import shared_task
from payments.models import Payment

release_by_wallet = BuyOrderReleaseByWallet()
release_by_ref = BuyOrderReleaseByReference()
release_by_rule = BuyOrderReleaseByRule()


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
        buy_order_release_by_reference_invoke.apply_async(args=[payment])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def sell_order_release_invoke():
    return sell_order_release()

