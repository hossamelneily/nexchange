from core.models import Pair
from orders.models import Order
from ticker.tests.base import TickerBaseTestCase
from rest_framework.test import APIClient
from support.models import Support


class BaseCoreApiTestCase(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC']
        super(BaseCoreApiTestCase, cls).setUpClass()
        cls.pair = Pair.objects.get(name='BTCLTC')
        cls.api_client = APIClient()

    def _create_order_api(self, amount_base=3, token=None):
        order_data = {
            "amount_base": amount_base,
            "pair": {
                "name": self.pair.name
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        if token is not None:
            self.api_client.credentials(
                Authorization="Bearer {}".format(token)
            )
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json').json()
        order = Order.objects.get(
            unique_reference=response['unique_reference']
        )
        token = response['token']
        return order, token

    def _create_support_ticket_api(self, msg, token=None):
        support_data = {
            'email': '{}@emil.com'.format(msg),
            'name': msg,
            'message': msg,
            'subject': msg,
        }
        if token is not None:
            self.api_client.credentials(
                Authorization="Bearer {}".format(token)
            )
        support_api_url = '/en/api/v1/support/'
        response = self.api_client.post(
            support_api_url, support_data, format='json').json()
        support = Support.objects.get(
            unique_reference=response['unique_reference']
        )
        return support
