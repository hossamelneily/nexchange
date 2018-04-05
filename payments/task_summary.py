from payments.models import Payment
from payments.tasks.generic.ok_pay import OkPayPaymentChecker
from payments.tasks.generic.payeer import PayeerPaymentChecker
from payments.tasks.generic.sofort import SofortPaymentChecker
from payments.tasks.generic.adv_cash import AdvCashPaymentChecker
from payments.tasks.generic.order_checker.base import \
    BaseFiatOrderDepositChecker
from payments.tasks.generic.payment_checker.base import \
    BasePaymentRefundChecker
from django.conf import settings
from celery import shared_task
from nexchange.utils import get_nexchange_logger
from orders.models import Order


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


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def run_adv_cash():
    # TODO: migrate to single instance
    adv_cash_checker = AdvCashPaymentChecker()
    return adv_cash_checker.run()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_fiat_order_deposit_invoke(order_pk):
    task = BaseFiatOrderDepositChecker()
    task.run(order_pk)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_fiat_order_deposit_periodic():
    logger = get_nexchange_logger('Periodic Fiat Order Deposit Checker')
    pending_fiat_orders = Order.objects.filter(
        flagged=False, status=Order.PAID_UNCONFIRMED, exchange=False
    )
    for order in pending_fiat_orders:
        try:
            check_fiat_order_deposit_invoke.apply_async([order.pk])
        except Exception as e:
            logger.logger.info(e)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_payments_for_refund_invoke(payment_pk):
    task = BasePaymentRefundChecker()
    task.run(payment_pk)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_payments_for_refund_periodic():
    logger = get_nexchange_logger('Periodic Fiat Order Refund Checker')
    payments = [
        p for p in Payment.objects.filter(
            is_success=True,
            flagged=False,
            order__status=Order.PAID_UNCONFIRMED
        ) if p.kyc_wait_period_expired
    ]
    for payment in payments:
        try:
            check_payments_for_refund_invoke.apply_async([payment.pk])
        except Exception as e:
            logger.logger.info(e)
