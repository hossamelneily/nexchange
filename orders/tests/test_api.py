from ticker.tests.base import TickerBaseTestCase
from rest_framework.test import APIClient
from orders.models import Order
from decimal import Decimal
from orders.api_views import OrderListViewSet
import os
from unittest.mock import patch
from core.tests.utils import data_provider
from nexchange.tests.test_ripple import RPC8_PORT, RPC8_PASSWORD, RPC8_USER,\
    RPC8_HOST, RPC13_PUBLIC_KEY_C1
from nexchange.tests.test_cryptonight import RPC12_PUBLIC_KEY_C1
from core.models import Currency, AddressReserve


class TestBestChangeAPI(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC', 'LTCBTC', 'LTCDOGE']
        super(TestBestChangeAPI, cls).setUpClass()
        cls.api_client = APIClient()

    def setUp(self):
        super(TestBestChangeAPI, self).setUp()
        self.addresses = {
            'LTC': 'LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4',
            'BTC': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
        }
        self.order1 = self._create_order_api(pair_name='LTCBTC')
        self.order_empty = self._create_order_api(pair_name='LTCBTC')
        self.order2 = self._create_order_api(
            pair_name='BTCLTC',
            address='1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
        )
        self.order3 = self._create_order_api(pair_name='LTCDOGE')
        assert self.order1.pair == self.order2.pair.reverse_pair
        self.order1.status = Order.COMPLETED
        self.order1.save()
        self.order2.status = Order.RELEASED
        self.order2.save()
        self.order3.status = Order.COMPLETED
        self.order3.save()

    def _create_order_api(self, pair_name='LTCBTC',
                          address='LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4',
                          amount=1):
        order_data = {
            'pair': {
                'name': pair_name
            },
            'withdraw_address': {
                'address': address
            },
            'amount_base': amount
        }
        order_api_url = '/en/api/v1/orders/'
        res = self.api_client.post(order_api_url, order_data, format='json')
        self.assertEqual(res.status_code, 201)
        order = Order.objects.latest('id')
        return order

    def test_plate_trade_history(self):
        res = self.api_client.get('/en/api/v1/trade_history/')
        self.assertEqual(res.status_code, 200)
        history = res.json()['results']
        self.assertEqual(len(history), 3)
        for _data in history:
            _order = Order.objects.get(
                unique_reference=_data['unique_reference']
            )
            self.assertEqual(_data['amount'], _order.amount_base)
            self.assertEqual(_data['pair'], _order.pair.name)
            self.assertEqual(_data['timestamp'], _order.created_on.timestamp())
            self.assertEqual(_data['trade_type'], 'BUY')
            self.assertEqual(_data['amount_currency'], _order.pair.base.code)
            self.assertEqual(Decimal(str(_data['price'])), _order.rate)

    def test_pair_trade_history(self):
        pair_name = 'BTCLTC'
        res = self.api_client.get('/en/api/v1/trade_history/?pair={}'.format(
            pair_name
        ))
        self.assertEqual(res.status_code, 200)
        history = res.json()['results']
        self.assertEqual(len(history), 2)
        for _data in history:
            _order = Order.objects.get(
                unique_reference=_data['unique_reference']
            )
            _reverse = False if pair_name == _order.pair.name else True
            if _reverse:
                self.assertEqual(pair_name, _order.pair.reverse_pair.name)
            amount = _order.amount_quote if _reverse else _order.amount_base
            order_type = 'SELL' if _reverse else 'BUY'
            amount_currency = \
                _order.pair.quote.code if _reverse else _order.pair.base.code
            price = _order.inverted_rate if _reverse else _order.rate
            self.assertEqual(Decimal(str(_data['amount'])), amount)
            self.assertEqual(_data['pair'], pair_name)
            self.assertEqual(_data['timestamp'], _order.created_on.timestamp())
            self.assertEqual(_data['trade_type'], order_type)
            self.assertEqual(_data['amount_currency'], amount_currency)
            self.assertEqual(Decimal(str(_data['price'])), price)

    def test_sort_trade_history(self):
        res_asc = self.api_client.get('/en/api/v1/trade_history/?sort=asc')
        res_desc = self.api_client.get('/en/api/v1/trade_history/?sort=desc')
        self.assertEqual(res_asc.status_code, 200)
        history_asc = res_asc.json()['results']
        history_desc = res_desc.json()['results']
        timestamp_asc = [o['timestamp'] for o in history_asc]
        timestamp_desc = [o['timestamp'] for o in history_desc]
        expected_asc = sorted(timestamp_asc)
        expected_desc = sorted(timestamp_asc)[::-1]
        self.assertEqual(timestamp_desc, expected_desc)
        self.assertEqual(timestamp_asc, expected_asc)


class TestFiatOrderPrivacy(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['LTCEUR']
        super(TestFiatOrderPrivacy, cls).setUpClass()
        cls.api_client = APIClient()
        cls.order_api_url = '/en/api/v1/orders/'
        cls.order_serializer = OrderListViewSet()

    def setUp(self):
        super(TestFiatOrderPrivacy, self).setUp()
        self.order_fiat = self._create_order_api(pair_name='LTCEUR')

    def _create_order_api(self, pair_name='LTCEUR',
                          address='LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4',
                          amount=1):
        order_data = {
            'pair': {
                'name': pair_name
            },
            'withdraw_address': {
                'address': address
            },
            'amount_base': amount
        }
        res = self.api_client.post(self.order_api_url,
                                   order_data, format='json')
        self.assertEqual(res.status_code, 201)
        order = Order.objects.latest('id')
        return order

    def _get_order_payment_url_api(self, order):
        res = self.api_client.get(
            '{}{}/'.format(self.order_api_url, order.unique_reference)
        )
        self.assertEqual(res.status_code, 200)
        return res.json()['payment_url']

    def test_show_payment_url_only_initial(self):
        payment_url1 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url1)
        self.order_fiat.status = Order.PAID_UNCONFIRMED
        self.order_fiat.save()
        payment_url2 = self._get_order_payment_url_api(self.order_fiat)
        self.assertEqual(payment_url2, None)

    def test_show_payment_url_only_to_creator(self):
        # create annother order - one order is a public case(means that no
        # private data is saved on payment window)
        self._create_order_api(pair_name='LTCEUR')
        self.assertEqual(self.order_fiat.user.orders.count(), 2)
        payment_url1 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url1)
        self.api_client.logout()
        payment_url2 = self._get_order_payment_url_api(self.order_fiat)
        self.assertEqual(payment_url2, None)

    def test_show_one_user_order_payment_url_to_everybody(self):
        self.assertEqual(self.order_fiat.user.orders.count(), 1)
        payment_url1 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url1)
        self.api_client.logout()
        payment_url2 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url2)

    def test_do_not_show_payment_url_on_list(self):
        res = self.api_client.get(self.order_api_url)
        self.assertEqual(res.status_code, 200)
        data = res.json()['results']
        self.assertEqual(len(data), 1)
        self.assertNotIn('payment_url', data[0])


class TestOrderParamsOnAddress(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['LTCXRP', 'XRPLTC', 'XMRLTC', 'LTCXMR',
                                    'XMRXRP', 'XRPXMR']
        super(TestOrderParamsOnAddress, cls).setUpClass()
        cls.api_client = APIClient()
        cls.order_api_url = '/en/api/v1/orders/'
        cls.order_serializer = OrderListViewSet()
        cls.patcher_validate_order_amount = patch(
            'orders.models.Order._validate_order_amount'
        )
        cls.patcher_validate_order_amount.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher_validate_order_amount.stop()

    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': RPC13_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': RPC8_PORT})
    def setUp(self):
        super(TestOrderParamsOnAddress, self).setUp()
        AddressReserve.objects.get_or_create(
            currency=Currency.objects.get(code='XRP'),
            address=RPC13_PUBLIC_KEY_C1,
        )
        AddressReserve.objects.get_or_create(
            currency=Currency.objects.get(code='XMR'),
            address=RPC12_PUBLIC_KEY_C1,
        )

    def _create_order_api(self, pair_name='LTCXRP',
                          address='LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4',
                          amount=1, destination_tag=None, payment_id=None):
        if pair_name == 'XRPXMR':
            address = 'r9y63YwVUQtTWHtwcmYc1Epa5KvstfUzSm'
        elif pair_name == 'XMRXRP':
            address = '44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3' \
                      'XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A'
        order_data = {
            'pair': {
                'name': pair_name
            },
            'withdraw_address': {
                'address': address,
                'destination_tag': destination_tag,
                'payment_id': payment_id
            },
            'amount_base': amount
        }
        res = self.api_client.post(self.order_api_url,
                                   order_data, format='json')
        return res

    def _get_order(self, order_reference):
        res = self.api_client.get(
            '{}{}/'.format(self.order_api_url, order_reference)
        )
        self.assertEqual(res.status_code, 200)
        return res.json()

    def _get_orders_list(self):
        res = self.api_client.get(self.order_api_url)
        self.assertEqual(res.status_code, 200)
        return res.json()

    @data_provider(lambda: (
            ('XMRXRP', '123456', '666c75666679706f6e79206973207468'
                                 '65206265737420706f6e792065766572', 400),
            ('XRPXMR', None, '666c75666679706f6e79206973207468'
                             '65206265737420706f6e792065766572', 400),
            ('XMRXRP', None, 'not right', 400),
            ('XRPXMR', 'not right', None, 400),
            ('XRPXMR', '1234567', None, 201),
            ('XMRXRP', None, '666c75666679706f6e79206973207468'
                             '65206265737420706f6e792065766572', 201),
    ), )
    def test_raise_error(self, pair_name, dest_tag, payment_id,
                         expected_res_code):
        res = self._create_order_api(
            pair_name=pair_name, destination_tag=dest_tag,
            payment_id=payment_id
        )
        self.assertEqual(res.status_code, expected_res_code, pair_name)

    def test_show_deposit_destination_tag(self):
        res = self._create_order_api()
        self.assertEqual(res.status_code, 201)
        post_res = res.json()
        deposit_address = post_res['deposit_address']
        withdraw_address = post_res['withdraw_address']
        self.assertIsNotNone(deposit_address['destination_tag'])
        self.assertIsNone(withdraw_address['destination_tag'])

        order_ref = post_res['unique_reference']
        order = Order.objects.get(unique_reference=order_ref)
        res = self._get_order(order_ref)
        deposit_address = res['deposit_address']
        withdraw_address = res['withdraw_address']
        self.assertIsNotNone(deposit_address['destination_tag'])
        self.assertIsNone(withdraw_address['destination_tag'])
        self.assertEqual(
            order.destination_tag,
            deposit_address['destination_tag']
        )

    def test_show_deposit_payment_id(self):
        res = self._create_order_api(pair_name='LTCXMR')
        self.assertEqual(res.status_code, 201)
        post_res = res.json()
        deposit_address = post_res['deposit_address']
        withdraw_address = post_res['withdraw_address']
        self.assertIsNotNone(deposit_address['payment_id'])
        self.assertIsNone(withdraw_address['payment_id'])

        order_ref = post_res['unique_reference']
        order = Order.objects.get(unique_reference=order_ref)
        res = self._get_order(order_ref)
        deposit_address = res['deposit_address']
        withdraw_address = res['withdraw_address']
        self.assertIsNotNone(deposit_address['payment_id'])
        self.assertIsNone(withdraw_address['payment_id'])
        self.assertEqual(
            order.payment_id,
            deposit_address['payment_id']
        )

    def test_withdraw_destination_tag(self):
        withdraw_address = 'r9y63YwVUQtTWHtwcmYc1Epa5KvstfUzSm'
        dest_tag = '123456'
        res = self._create_order_api(pair_name='XRPLTC',
                                     address=withdraw_address,
                                     destination_tag=dest_tag, amount=10)
        self.assertEqual(res.status_code, 201)
        post_res = res.json()
        order_ref = post_res['unique_reference']
        destination_tag = post_res['withdraw_address'].get('destination_tag')
        order = Order.objects.get(unique_reference=order_ref)
        self.assertEqual(order.destination_tag, dest_tag)
        self.assertEqual(destination_tag, dest_tag)
        res = self._get_order(order_ref)
        get_destination_tag = res['withdraw_address'].get('destination_tag')
        self.assertEqual(get_destination_tag, dest_tag)

    def test_withdraw_payment_id(self):
        withdraw_address = \
            '44AFFq5kSiAAaA4AAAaAaA18obc8AemS33DBLWs3H7otXft' \
            '3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A'
        payment_id = '12345678901234567890123456789000' \
                     '12345678901234567890123456789000'
        res = self._create_order_api(pair_name='XMRLTC',
                                     address=withdraw_address,
                                     payment_id=payment_id, amount=10)
        self.assertEqual(res.status_code, 201)
        post_res = res.json()
        order_ref = post_res['unique_reference']
        payment_id_res = post_res['withdraw_address'].get('payment_id')
        order = Order.objects.get(unique_reference=order_ref)
        self.assertEqual(order.payment_id, payment_id)
        self.assertEqual(payment_id_res, payment_id)
        res = self._get_order(order_ref)
        get_payment_id = res['withdraw_address'].get('payment_id')
        self.assertEqual(get_payment_id, payment_id)
