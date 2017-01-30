from core.models import Transaction, Address
from orders.models import Order
from core.tests.base import OrderBaseTestCase, UserBaseTestCase
import requests_mock
from accounts.tasks.schedule.monitor_wallets import (
    import_transactions_deposit_btc
)
from unittest import skip


class MonitorTestCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(MonitorTestCase, self).setUp()
        self.wallet_address = '198aMn6ZYAczwrE5NvNTUMyJ5qkfy4g3Hi'
        self.address = Address(
            name='test address',
            address=self.wallet_address,
            currency=self.BTC,
            user=self.user,
            type=Address.DEPOSIT
        )
        self.address.save()
        self.url = 'http://btc.blockr.io/api/v1/address/txs/{}'.format(
            self.wallet_address
        )

    @skip('Need to Finish order')
    @requests_mock.mock()
    def test_create_transactions_with_task(self, m):
        cont_path = 'nexchange/tests/fixtures/blockr/address_transactions.json'
        with open(cont_path) as f:
            m.get(self.url, text=f.read().replace('\n', ''))
        order = Order(
            order_type=Order.SELL,
            amount_btc=0.1
        )
        order.save()
        import_transactions_deposit_btc()
        Transaction.objects.filter()
