from core.models import Transaction, Address
from orders.models import Order
from core.tests.base import OrderBaseTestCase
import requests_mock
from accounts.tasks.monitor_wallets import BlockchainTransactionChecker
import json
from decimal import Decimal


class MonitorTestCase(OrderBaseTestCase):

    def setUp(self):
        super(MonitorTestCase, self).setUp()
        self._read_fixture()
        self.address = Address(
            name='test address',
            address=self.wallet_address,
            currency=self.BTC,
            user=self.user,
            type=Address.DEPOSIT
        )
        self.address.save()
        self.task = BlockchainTransactionChecker(self.address)
        self.url = 'http://btc.blockr.io/api/v1/address/txs/{}'.format(
            self.wallet_address
        )

    def _read_fixture(self):
        cont_path = 'nexchange/tests/fixtures/blockr/address_transactions.json'
        with open(cont_path) as f:
            self.blockr_response = f.read().replace('\n', '')
            self.wallet_address = json.loads(self.blockr_response)['data'][
                'address'
            ]
            txs = json.loads(self.blockr_response)['data']['txs']
            self.amounts = [tx['amount'] for tx in txs]
            self.tx_ids = [tx['tx'] for tx in txs]

    @requests_mock.mock()
    def test_create_transactions_with_task(self, m):
        m.get(self.url, text=self.blockr_response)
        status_ok_list_index = 0
        status_bad_list_index = 1
        order = Order(
            order_type=Order.SELL,
            amount_btc=Decimal(str(self.amounts[status_ok_list_index])),
            currency=self.EUR,
            user=self.user,
            is_completed=False,
            is_paid=False
        )
        order.save()
        unique_ref = order.unique_reference
        self.task.run()
        tx_ok = Transaction.objects.filter(
            tx_id=self.tx_ids[status_ok_list_index]
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created if order is found!'
        )
        order = Order.objects.get(unique_reference=unique_ref)
        self.assertTrue(
            order.is_paid,
            'Order should be marked as paid after transaction import'
        )
        tx_bad = Transaction.objects.filter(
            tx_id=self.tx_ids[status_bad_list_index]
        )
        self.assertEqual(
            len(tx_bad), 0,
            'Transaction must not be created if order is not found!'
        )
        self.task.run()
        tx_ok = Transaction.objects.filter(
            tx_id=self.tx_ids[status_ok_list_index]
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created only one time!'
        )
