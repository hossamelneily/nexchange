from django.core.management import BaseCommand
from audit.tasks.generic.suspicious_transactions_checker import \
    SuspiciousTransactionsChecker


class Command(BaseCommand):
    help = "Check transactions"

    def handle(self, *args, **options):
        checker = SuspiciousTransactionsChecker(do_log=False)
        for curr in ['XVG', 'BTC', 'BCH', 'LTC', 'DOGE', 'ETH']:
            checker.run(curr)
