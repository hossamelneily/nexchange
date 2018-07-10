from ticker.tests.base import TickerBaseTestCase
from rest_framework.test import APIClient
from orders.models import Order
from decimal import Decimal
from datetime import timedelta, datetime
from freezegun import freeze_time
from orders.api_views import OrderListViewSet


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
        self.assertEqual(payment_url2, '')

    def test_show_payment_url_only_non_expired(self):
        payment_url1 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url1)
        now = datetime.now() + timedelta(
            minutes=self.order_fiat.payment_window)
        with freeze_time(now):
            payment_url2 = self._get_order_payment_url_api(self.order_fiat)
            self.assertEqual(payment_url2, '')

    def test_show_payment_url_only_to_creator(self):
        payment_url1 = self._get_order_payment_url_api(self.order_fiat)
        self.assertIn(self.order_fiat.unique_reference, payment_url1)
        self.api_client.logout()
        payment_url2 = self._get_order_payment_url_api(self.order_fiat)
        self.assertEqual(payment_url2, '')

    def test_do_not_show_payment_url_on_list(self):
        res = self.api_client.get(self.order_api_url)
        self.assertEqual(res.status_code, 200)
        data = res.json()['results']
        self.assertEqual(len(data), 1)
        self.assertNotIn('payment_url', data[0])
