from datetime import timedelta, datetime
from unittest.mock import patch

from django.conf import settings

from core.models import Pair
from orders.models import Order
from ticker.tests.base import TickerBaseTestCase
from freezegun import freeze_time
from rest_framework.test import APIClient
from oauth2_provider.models import Application, AccessToken
from core.tests.utils import data_provider
from support.models import Support


class Oauth2TestCase(TickerBaseTestCase):

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['BTCLTC']
        super(Oauth2TestCase, self).setUp()
        self.pair = Pair.objects.get(name='BTCLTC')
        self.api_client = APIClient()

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

    def test_no_token_on_detail_view(self):
        order, _token = self._create_order_api()
        response = self.api_client.get(
            '/en/api/v1/orders/{}/'.format(order.unique_reference),
            format='json').json()
        resp_token = response.get('token')
        self.assertIsNone(resp_token)

    def test_token_created(self):
        order, _token = self._create_order_api()
        user = order.user
        app = Application.objects.get(user=user)
        self.assertEqual(app.name, user.username)
        self.assertEqual(app.client_type, app.CLIENT_CONFIDENTIAL)
        self.assertEqual(app.authorization_grant_type, app.GRANT_PASSWORD)
        token = AccessToken.objects.get(user=user, application=app)
        self.assertFalse(token.is_expired())
        self.assertTrue(token.is_valid())
        self.assertEqual(_token, token.token)
        now = datetime.now() + timedelta(
            seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS + 1
        )
        with freeze_time(now):
            self.assertTrue(token.is_expired())
            self.assertFalse(token.is_valid())

    def test_login_with_token(self):
        order1, _token1 = self._create_order_api()
        self.api_client.logout()
        order2, _token2 = self._create_order_api()
        self.api_client.logout()
        order3, _token3 = self._create_order_api(token=_token1)
        self.assertEqual(order1.user, order3.user)
        self.assertNotEqual(order1.user, order2.user)
        self.assertNotEqual(_token1, _token2)
        self.assertIsNone(_token3)
        self.assertIsNotNone(_token1)
        self.assertIsNotNone(_token2)

    def test_create_new_user_after_expiration(self):
        order1, _token1 = self._create_order_api()
        self.api_client.logout()
        order2, _token2 = self._create_order_api(token=_token1)
        self.api_client.logout()
        now = datetime.now() + timedelta(
            seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS + 1
        )
        with freeze_time(now):
            order3, _token3 = self._create_order_api(token=_token1)

        self.assertEqual(order1.user, order2.user)
        self.assertNotEqual(order1.user, order3.user)
        self.assertNotEqual(_token1, _token3)

    @data_provider(lambda: (
        ('',),
        ('bad_token',),
        ('5522 2asd5das asdf',),
    ))
    def test_create_order_with_bad_token(self, bad_token):
        order, _token = self._create_order_api(token='')
        token = AccessToken.objects.get(user=order.user)
        self.assertEqual(token.token, _token)
        self.assertNotEqual(bad_token, _token)
        self.api_client.logout()

    @data_provider(lambda: (
        ('',),
        ('Bearer',),
        ('Bearer ',),
        ('Beaber Justin',),
        ('Token smoke alot',),
    ))
    def test_create_order_with_bad_header(self, bad_header):
        self.api_client.credentials(Authorization=bad_header)
        order, _token = self._create_order_api()
        token = AccessToken.objects.get(user=order.user)
        self.assertEqual(token.token, _token)
        self.api_client.logout()

    def test_no_token_if_user_has_more_than_one_order(self):
        order1, _token1 = self._create_order_api()
        self.assertEqual(order1.token, _token1)
        self.assertIsNotNone(_token1)
        order2, _token2 = self._create_order_api()
        self.assertEqual(order1.user, order2.user)
        self.assertEqual(order2.token, _token2)
        self.assertIsNone(_token2)

    def test_support_user_after_order_created(self):
        support_anonymous = self._create_support_ticket_api('msg1')
        self.assertIsNone(support_anonymous.user)
        self.assertEqual(support_anonymous.user_orders, [])
        self.api_client.logout()
        order, _token = self._create_order_api()
        self.api_client.logout()
        support = self._create_support_ticket_api('msg', token=_token)
        self.assertEqual(support.user, order.user)
        self.assertIn(order, support.user_orders)

    @patch('orders.models.AccessToken.is_valid')
    def test_not_valid_token_is_not_returned(self, is_valid):
        is_valid.return_value = False
        order, _token = self._create_order_api()
        self.assertIsNone(_token)

    @patch('orders.api_views.OrderListViewSet._create_bearer_token')
    def test_empty_token_returned_when_token_is_not_created(self,
                                                            create_token):
        order, _token = self._create_order_api()
        self.assertIsNone(_token)
