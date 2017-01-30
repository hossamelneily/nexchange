from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from celery import shared_task


@shared_task()
def run_payeer():
    instance = PayeerPaymentChecker()
    return instance.run()


@shared_task()
def run_okpay():
    instance = OkPayPaymentChecker()
    return instance.run()
