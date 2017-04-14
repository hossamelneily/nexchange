from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from payments.tasks.generic.sofort import SofortPaymentChecker
from django.conf import settings
from celery import shared_task


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_payeer():
    # TODO: migrate to single instance
    payeer_checker = PayeerPaymentChecker()
    return payeer_checker.run()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_okpay():
    # TODO: migrate to single instance
    okpay_checker = OkPayPaymentChecker()
    return okpay_checker.run()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_sofort():
    # TODO: migrate to single instance
    sofort_checker = SofortPaymentChecker()
    return sofort_checker.run()
