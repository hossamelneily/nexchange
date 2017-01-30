from accounts.tests.base import TransactionImportBaseTestCase
from orders.models import Order
import requests_mock
from accounts.tasks.monitor_wallets import import_transaction_deposit_btc
from orders.tasks.order_release import sell_order_release


class SellOrderReleaseTaskTestCase(TransactionImportBaseTestCase):

    def setUp(self):
        super(SellOrderReleaseTaskTestCase, self).setUp()
        self.import_txs_task = import_transaction_deposit_btc
        self.release_task = sell_order_release

    @requests_mock.mock()
    def test_create_transactions_with_task(self, m):
        m.get(self.url, text=self.blockr_response)
        self.import_txs_task.apply()
        self.release_task.apply()
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertTrue(order.is_released)
