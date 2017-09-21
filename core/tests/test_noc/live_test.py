from core.tests.test_noc.base import BaseTestLiveOrders
import time


class TestLiveOrders(BaseTestLiveOrders):

    def setup(self):
        super(TestLiveOrders, self).setup()

    def test_create_live_order_with_api(self):
        order_res = self.create_order(amount_base=self.random_amount(
            min_val=200, max_val=250, multiplier=0.00001))
        amount = order_res.get('deposit_amount')
        address = order_res.get('deposit_address')
        self.send_funds_eth_wallet(amount, address)
        print()
        print(order_res)
        order_ref = order_res.get('order', {}).get('unique_reference')
        print()
        print(self.order_endpoint(ref=order_ref))
        time.sleep(10)
        outgoing_tx_id = self.get_transaction_id_from_eth_wallet_success_msg()
        self.check_tx_till_paid_status(order_ref, outgoing_tx_id)
