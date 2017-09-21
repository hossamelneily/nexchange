from core.tests.test_noc.base import BaseTestLiveOrders
import requests
import ipdb
from unittest import skip


@skip('stashed')
class TestLiveCheckListOrders(BaseTestLiveOrders):

    def setUp(self):
        super(TestLiveCheckListOrders, self).setUp()
        self.list = ['ODO1AN']
        self.private_key = 'block' # private key of https://www.myetherwallet.com  # noqa

    def get_order(self, ref):
        url = self.order_endpoint(ref=ref)
        return requests.get(url).json()

    def get_order_transaction(self, order, type='D'):
        txns = order.get('transactions', [])
        txn = [txn for txn in txns if txn['type'] == 'D']
        if len(txn) == 0:
            return None
        else:
            return txn[0]

    def test_list(self):
        for ref in self.list:
            order = self.get_order(ref)
            txn = self.get_order_transaction(order)
        ipdb.set_trace()

