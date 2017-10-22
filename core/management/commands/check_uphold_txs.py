from core.models import Transaction
from django.core.management import BaseCommand
from nexchange.api_clients.uphold import UpholdApiClient

UPHOLD = UpholdApiClient()


class Command(BaseCommand):
    help = "Check Uphold transactions"

    def get_uphold_deposit_transactions(self):
        uphold_deposit_txs = Transaction.objects.filter(
            currency__wallet='api1', type=Transaction.DEPOSIT)
        res = [{'pk': tx.pk, 'tx_id_api': tx.tx_id_api, 'tx_id': tx.tx_id,
                'amount': tx.amount, 'currency': tx.currency.code} for tx in
               uphold_deposit_txs if not tx.tx_id_api]
        return res

    def get_last_txs(self, count=1400):
        last_txs = []
        for i in range(0, count, 50):
            items = 'items={}-{}'.format(i, i + 49)
            UPHOLD.api.headers.update({'Range': items})
            last_txs += UPHOLD.api.get_transactions()
        UPHOLD.api.headers.update({'Range': 'items=0-49'})
        return [tx for tx in last_txs if not isinstance(tx, str)]

    def get_last_txs_ids(self):
        last_txs = self.get_last_txs()
        return [
            tx.get('params', {}).get('txid')
            for tx in last_txs if 'txid' in tx.get('params', {})
        ]

    # A command must define handle()
    def handle(self, *args, **options):
        txs = self.get_uphold_deposit_transactions()
        last_ids = self.get_last_txs_ids()
        suspicious_txs = [tx for tx in txs if tx.get('tx_id') not in last_ids]
        print('Suspicious txs:')
        print(suspicious_txs)
