from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from django.conf import settings
from celery import shared_task


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_payeer():
    instance = PayeerPaymentChecker()
    return instance.run()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_okpay():
    instance = OkPayPaymentChecker()
    return instance.run()
