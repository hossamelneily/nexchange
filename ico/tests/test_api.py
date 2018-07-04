from ticker.tests.base import TickerBaseTestCase
from rest_framework.test import APIClient
from orders.models import Order
from unittest.mock import patch
from ico.models import Subscription
import os
from decimal import Decimal
from ticker.models import Price
from ico.task_summary import subscription_checker_periodic


class TestIcoAPI(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['ETHBTC', 'BDGETH']
        super(TestIcoAPI, cls).setUpClass()
        cls.api_client = APIClient()

    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': '0xmain_card'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    def setUp(self):
        super(TestIcoAPI, self).setUp()
        # leave some upper/lower test case on this address -
        # for ETH it does not matter
        self.eth_address = '0x8116546AaC209EB58c5B531011ec42DD28EdFb71'
        self.email = 'unit@test.qa'
        self.order_eth = self._create_order_api(pair_name='ETHBTC')
        self.order_bdg = self._create_order_api(pair_name='BDGETH',
                                                amount=1000)
        self.order_eth.status = Order.COMPLETED
        self.order_eth.save()
        self.order_bdg.status = Order.RELEASED
        self.order_bdg.save()

    def _create_order_api(self, pair_name='ETHBTC',
                          amount=1):
        order_data = {
            'pair': {
                'name': pair_name
            },
            'withdraw_address': {
                'address': self.eth_address.lower()
            },
            'amount_base': amount
        }
        order_api_url = '/en/api/v1/orders/'
        res = self.api_client.post(order_api_url, order_data, format='json')
        self.assertEqual(res.status_code, 201)
        order = Order.objects.latest('id')
        return order

    def _create_subscription_api(self):
        order_data = {
            'email': self.email,
            'sending_address': self.eth_address,
        }
        order_api_url = '/en/api/v1/ico/subscription/'
        res = self.api_client.post(order_api_url, order_data, format='json')
        self.assertEqual(res.status_code, 201)
        return Subscription.objects.get(**res.json())

    @patch('web3.eth.Eth.getBalance')
    def test_subscription_params_checked(self, get_balance):
        """ It is assumed that parameters are checkeck by invoking task
        after Subscrition is created """

        expected_balance = Decimal('11.11')
        eth = self.order_eth.pair.base
        get_balance.return_value = int(
            Decimal('11.11') * Decimal('1e{}'.format(eth.decimals))
        )
        expected_address_turnover = \
            self.order_eth.amount_base \
            + Price.convert_amount(self.order_bdg.amount_base, 'BDG', 'ETH')
        sub = self._create_subscription_api()
        sub.refresh_from_db()
        self.assertEqual(sub.eth_balance, expected_balance)
        self.assertEqual(sub.address_turnover, expected_address_turnover)
        with patch('ico.tasks.generic.eth_balance_checker.'
                   'EthBalanceChecker.run') as bal:
            subscription_checker_periodic.apply_async()
            bal.assert_called_once()
        with patch('ico.tasks.generic.address_turnover_checker.'
                   'AddressTurnoverChecker.run') as turn:
            subscription_checker_periodic.apply_async()
            turn.assert_called_once()
