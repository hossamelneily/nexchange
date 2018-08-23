from decimal import Decimal

from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Currency
from core.tests.base import OrderBaseTestCase
from orders.models import Order
from ticker.tests.base import TickerBaseTestCase
from risk_management.models import Account
from unittest.mock import patch
from core.models import Pair


class OrderIndexOrderTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderIndexOrderTestCase, self).setUp()

    def test_redirect_login_for_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('referrals.main'))
        self.assertEqual(302, response.status_code)

        success = self.client.login(
            username=self.username, password=self.password)
        self.assertTrue(success)


class TestGetPrice(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC', 'LTCBTC', 'XVGBTC']
        cls.cls_patcher_validate_ticker_diff = patch(
            'ticker.models.Ticker._validate_change'
        )
        cls.cls_patcher_validate_ticker_diff.start()
        super(TestGetPrice, cls).setUpClass()
        cls.api_client = APIClient()
        cls.get_price_url = '/en/api/v1/get_price/{}/'

    @classmethod
    def tearDownClass(cls):
        super(TestGetPrice, cls).tearDownClass()
        cls.cls_patcher_validate_ticker_diff.stop()

    def tearDown(self):
        super(TestGetPrice, self).tearDown()
        # Purge
        Order.objects.all().delete()

    def test_return_correct_quote(self):
        client = APIClient()
        amount_base = 0.05
        pair_name = 'BTCEUR'
        get_price_quote = client.get(
            self.get_price_url.format(pair_name),
            data={'amount_base': amount_base}
        ).data['amount_quote']

        data = {
            "amount_base": amount_base,
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        new_order_quote = client.post('/en/api/v1/orders/', data=data,
                                      format='json').data['amount_quote']
        self.assertEqual(Decimal(get_price_quote), Decimal(new_order_quote))

    def test_return_correct_base(self):
        client = APIClient()
        amount_quote = 200
        pair_name = 'BTCEUR'
        get_price_base = client.get(
            self.get_price_url.format(pair_name),
            data={'amount_quote': amount_quote}
        ).data['amount_base']

        data = {
            "amount_quote": amount_quote,
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": "17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ"
            }
        }
        new_order_base = client.post('/en/api/v1/orders/', data=data,
                                     format='json').data['amount_base']
        self.assertEqual(Decimal(get_price_base), Decimal(new_order_base))

    def test_does_not_create_order(self):
        orders_before = Order.objects.count()
        client = APIClient()
        res = client.get(self.get_price_url.format('BTCEUR'),
                         data={'amount_base': 0.05})
        self.assertEqual(res.status_code, 200)
        orders_after = Order.objects.count()
        self.assertEqual(orders_before, orders_after)

    def test_bad_requests(self):
        client = APIClient()
        pair = Pair.objects.get(name='BTCEUR')
        max_amount = pair.base.maximal_amount
        res_ok_pair = client.get(self.get_price_url.format(pair.name),
                                 data={'amount_base': max_amount * 2 + 1})
        self.assertEqual(res_ok_pair.status_code, 400)

        data = res_ok_pair.json()
        ref_order = Order(pair=pair)
        self.assertEqual(
            Decimal(str(data['max_amount_quote'])),
            ref_order.get_amount_quote_max(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['max_amount_base'])),
            ref_order.get_amount_base_max(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['min_amount_base'])),
            ref_order.get_amount_base_min(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['min_amount_quote'])),
            ref_order.get_amount_quote_min(user_format=True)
        )

        res = client.get(self.get_price_url.format('BTCxxx/'),
                         data={'amount_base': 100})
        self.assertEqual(res.status_code, 404)

    def test_get_price_without_params(self):
        pair_name = 'BTCEUR'
        pair = Pair.objects.get(name=pair_name)
        res = self.api_client.get(self.get_price_url.format(pair_name))
        data = res.json()
        self.assertEqual(
            data['amount_quote'],
            settings.DEFAULT_FIAT_ORDER_DEPOSIT_AMOUNT
        )
        res = self.api_client.get(self.get_price_url.format('LTCBTC'))
        self.BTC.refresh_from_db()
        self.assertEqual(
            Decimal(str(res.json()['amount_quote'])),
            settings.DEFAULT_CRYPTO_ORDER_DEPOSIT_AMOUNT_MULTIPLIER *
            self.BTC.minimal_amount
        )
        self.assertEqual(data['pair']['quote'], pair.quote.code)
        self.assertEqual(data['pair']['base'], pair.base.code)
        ref_order = Order(pair=pair)
        self.assertEqual(
            Decimal(str(data['max_amount_quote'])),
            ref_order.get_amount_quote_max(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['max_amount_base'])),
            ref_order.get_amount_base_max(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['min_amount_base'])),
            ref_order.get_amount_base_min(user_format=True)
        )
        self.assertEqual(
            Decimal(str(data['min_amount_quote'])),
            ref_order.get_amount_quote_min(user_format=True)
        )

    def test_reserves_less_than_default_fiat(self):
        btc = Currency.objects.get(code='BTC')
        res_with_quote = self.api_client.get(
            self.get_price_url.format('BTCEUR'),
            data={'amount_quote': settings.DEFAULT_FIAT_ORDER_DEPOSIT_AMOUNT})
        quote_data = res_with_quote.json()
        account = Account.objects.get(reserve__currency__code='BTC',
                                      is_main_account=True)
        account.available = Decimal(quote_data['amount_base']) * Decimal(0.9)
        account.save()
        res_default = self.api_client.get(self.get_price_url.format('BTCEUR'))
        self.assertEqual(res_default.status_code, 200)
        default_data = res_default.json()
        self.assertTrue(
            default_data['amount_base'] < quote_data['amount_base']
        )
        self.assertTrue(
            default_data['amount_quote'] < quote_data['amount_quote']
        )
        # Move BTC to executable (maximal can be more thann reserves)
        btc.execute_cover = True
        btc.save()
        res_default_cover = self.api_client.get(
            self.get_price_url.format('BTCEUR')
        )
        self.assertEqual(res_default_cover.status_code, 200)
        default_cover_data = res_default_cover.json()
        self.assertEqual(
            default_cover_data['amount_base'],
            quote_data['amount_base']
        )
        self.assertEqual(
            default_cover_data['amount_quote'],
            quote_data['amount_quote']
        )

    def test_default_less_than_minimum_fiat(self):
        res_with_quote = self.api_client.get(
            self.get_price_url.format('BTCEUR'),
            data={'amount_quote': settings.DEFAULT_FIAT_ORDER_DEPOSIT_AMOUNT})
        quote_data = res_with_quote.json()
        self.BTC.minimal_amount = \
            Decimal(quote_data['amount_base']) * Decimal(1.1)
        self.BTC.save()
        res_default = self.api_client.get(self.get_price_url.format('BTCEUR'))
        self.assertEqual(res_default.status_code, 200)
        default_data = res_default.json()
        self.assertTrue(
            default_data['amount_base'] > quote_data['amount_base']
        )
        self.assertTrue(
            default_data['amount_quote'] > quote_data['amount_quote']
        )

    def test_maximal_quote_less_tha_default(self):
        ltc = Currency.objects.get(code='LTC')
        normal_default = \
            ltc.minimal_amount * \
            settings.DEFAULT_CRYPTO_ORDER_DEPOSIT_AMOUNT_MULTIPLIER
        res_with_quote = self.api_client.get(
            self.get_price_url.format('BTCLTC'),
            data={'amount_quote': normal_default})
        quote_data = res_with_quote.json()
        ltc.maximal_amount = normal_default * Decimal(0.8)
        ltc.save()
        res_default = self.api_client.get(self.get_price_url.format('BTCLTC'))
        self.assertEqual(res_default.status_code, 200)
        default_data = res_default.json()
        self.assertTrue(
            default_data['amount_base'] < quote_data['amount_base']
        )
        self.assertTrue(
            default_data['amount_quote'] < quote_data['amount_quote']
        )

    def test_raise_error_on_less_than_minimal_fiat(self):
        EUR = Currency.objects.get(code='EUR')
        minimal_amount = EUR.minimal_amount
        res = self.api_client.get(
            self.get_price_url.format('BTCEUR'),
            data={'amount_quote': minimal_amount * Decimal(0.9)})
        self.assertEqual(res.status_code, 400)

    def test_do_not_raise_error_on_less_than_minimal_crypto(self):
        BTC = Currency.objects.get(code='BTC')
        minimal_amount = BTC.minimal_amount
        res = self.api_client.get(
            self.get_price_url.format('XVGBTC'),
            data={'amount_quote': minimal_amount * Decimal(0.9)})
        self.assertEqual(res.status_code, 200)
