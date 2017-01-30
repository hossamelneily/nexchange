from orders.tasks.order_release import buy_order_release
from .tasks.order_release import sell_order_release
from django.conf import settings
from celery import shared_task


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def buy_order_release_invoke():
    return buy_order_release()

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def sell_order_release_invoke():
    return sell_order_release()
