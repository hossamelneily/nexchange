from django.conf import settings
from celery import shared_task
from core.models import Currency
from nexchange.utils import get_nexchange_logger

from .tasks.generic.suspicious_transactions_checker import \
    SuspiciousTransactionsChecker


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_suspicious_transactions_invoke(currency):
    checker = SuspiciousTransactionsChecker(do_print=False)
    checker.run(currency)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_suspicious_transactions_all_currencies_periodic():
    logger = get_nexchange_logger('Suspicious Transaction Checker')
    for curr in Currency.objects.filter(disabled=False, is_crypto=True,
                                        is_token=False):
        try:
            check_suspicious_transactions_invoke.apply_async([curr])
        except Exception as e:
            logger.warning(e)
            continue
