from django.conf import settings
from celery import shared_task

from .tasks.generic.suspicious_transactions_checker import \
    SuspiciousTransactionsChecker


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_suspicious_transactions_invoke(currency_code):
    checker = SuspiciousTransactionsChecker(do_print=False)
    checker.run(currency_code)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_suspicious_transactions_all_currencies_invoke():
    for curr in ['XVG', 'BTC', 'BCH', 'LTC', 'DOGE', 'ETH', 'ZEC']:
        try:
            check_suspicious_transactions_invoke.apply_async([curr])
        except:
            continue
