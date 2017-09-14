from orders.models import Order
from core.models import Transaction
from django.core.management import BaseCommand


class Command(BaseCommand):
    # Show this when the user types help
    help = "Migrate order statuses to incremental statuses"

    def fix_replay_txns(self):
        orders = Order.objects.all()
        for order in orders:
            dep_txns = order.transactions.filter(
                type=Transaction.DEPOSIT).order_by('pk')
            with_txns = order.transactions.filter(
                type=Transaction.WITHDRAW).order_by('pk')
            for txns in [dep_txns, with_txns]:
                if len(txns) <= 1:
                    continue
                for i, txn in enumerate(txns):
                    if i == 0:
                        continue
                    if txn.admin_comment not in [None, '']:
                        continue
                    msg = 'replay {}'.format(i)
                    txn.admin_comment = msg
                    txn.flag(msg)
                    txn.save()

    def fix_without_type_txns(self):
        other_txns = Transaction.objects.exclude(
            type=Transaction.WITHDRAW).exclude(
            type=Transaction.DEPOSIT).order_by('pk')
        for i, txn in enumerate(other_txns):
            if txn.admin_comment not in [None, '']:
                continue
            msg = 'no transaction type {}'.format(i + 1)
            txn.admin_comment = msg
            txn.flag(msg)
            txn.save()

    # A command must define handle()
    def handle(self, *args, **options):
        self.fix_without_type_txns()
        self.fix_replay_txns()

        self.stdout.write("Reply and without type transactions fixed.")
