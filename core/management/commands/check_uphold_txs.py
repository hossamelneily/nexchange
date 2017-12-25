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

    def get_uphold_transactions_ids_lists(self):
        uphold_txs = Transaction.objects.filter(
            currency__wallet='api1')
        tx_ids = [tx.tx_id for tx in uphold_txs]
        tx_api_ids = [tx.tx_id_api for tx in uphold_txs]
        return tx_ids, tx_api_ids

    def get_last_txs(self, count=2500):
        last_txs = []
        for i in range(0, count, 50):
            items = 'items={}-{}'.format(i, i + 49)
            UPHOLD.api.headers.update({'Range': items})
            last_txs += UPHOLD.api.get_transactions()
        UPHOLD.api.headers.update({'Range': 'items=0-49'})
        return [tx for tx in last_txs if not isinstance(tx, str)]

    def get_last_txs_ids(self):
        last_txs = self.get_last_txs()
        last_ids = [
            tx.get('params', {}).get('txid')
            for tx in last_txs if 'txid' in tx.get('params', {})
        ]
        last_uphold_ids = [
            {
                'tx_id_api': tx.get('id', 'None'),
                'tx_id': tx.get('params', {}).get('txid', 'None'),
                'type': tx.get('params', {}).get('type', 'None'),
                'currency': tx.get('params', {}).get('currency', 'None'),
                'amount': tx.get('destination', {}).get('amount', 'None'),
                'address': tx.get('destination', {}).get('address', 'None'),
                'created_at': tx.get('createdAt'),
            } for tx in last_txs
        ]
        return last_ids, last_uphold_ids

    # A command must define handle()
    def handle(self, *args, **options):
        deposit_txs = self.get_uphold_deposit_transactions()
        last_ids, last_uphold_ids = self.get_last_txs_ids()
        suspicious_txs = [
            tx for tx in deposit_txs if tx.get('tx_id') not in last_ids]
        print('Suspicious txs:')
        print(suspicious_txs)
        tx_ids, tx_api_ids = self.get_uphold_transactions_ids_lists()
        not_tracked_txs = [
            tx for tx in last_uphold_ids if all([
                tx.get('tx_id') not in tx_ids,
                tx.get('tx_id_api') not in tx_api_ids,
                tx.get('type') != 'transfer'
            ])
        ]
        print('Not tracked txs:')
        for tx in not_tracked_txs[::-1]:
            print(tx['created_at'], tx['currency'], tx['amount'],
                  tx['address'], tx['tx_id'], tx['tx_id_api'], tx['type'])
