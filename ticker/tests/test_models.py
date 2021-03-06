from core.tests.utils import enable_all_pairs
from django.db.models import Q
from django.conf import settings

from unittest.mock import patch
from datetime import timedelta, datetime
from freezegun import freeze_time
from decimal import Decimal

from .base import TickerBaseTestCase
from core.models import Currency, Pair
from ticker.models import Price, Ticker
from django.test import TestCase
from django.core.exceptions import ValidationError
import requests_mock
from core.models import FeeDiscount
from core.tests.base import OrderBaseTestCase
from ticker.task_summary import get_all_tickers_force
from ticker.adapters import BittrexAdapter
from ticker.tests.fixtures.bittrex.market_resp import \
    resp as bittrex_market_resp


class PriceValidatorsTestCase(TestCase):

    fixtures = [
        'market.json',
        'currency_algorithm.json',
        'currency_crypto.json',
        'currency_tokens.json',
        'pairs_cross.json',
        'transaction_price.json',
    ]

    def setUp(self):
        super(PriceValidatorsTestCase, self).setUp()
        self.pair = Pair.objects.get(name='LTCBTC')

    def test_do_not_create_price_without_ticker(self):
        with self.assertRaises(ValidationError):
            Price.objects.create(pair=self.pair)

    def test_do_not_save_ticker_too_big_difference(self):
        patch.stopall()
        for ticker in Ticker.objects.all():
            price = Price.objects.get(ticker=ticker)
            price.delete()
            ticker.delete()
        self.assertEqual(Ticker.objects.all().count(), 0)
        ask = Decimal('1.1')
        bid = Decimal('0.9')
        ticker1 = Ticker(pair=self.pair, ask=ask, bid=bid)
        ticker1.save()
        Price.objects.create(pair=self.pair, ticker=ticker1)
        self.assertEqual(Ticker.objects.all().count(), 1)
        ticker2 = Ticker(pair=self.pair, ask=ask, bid=bid)
        ticker2.save()
        Price.objects.create(pair=self.pair, ticker=ticker2)
        self.assertEqual(Ticker.objects.all().count(), 2)
        positive_multiplier = \
            Decimal('1.0001') + settings.TICKER_ALLOWED_CHANGE
        negative_multiplier = \
            Decimal('0.99990') - settings.TICKER_ALLOWED_CHANGE
        with self.assertRaises(ValidationError):
            Ticker.objects.create(
                pair=self.pair, ask=ask * positive_multiplier, bid=bid
            )
        with self.assertRaises(ValidationError):
            Ticker.objects.create(
                pair=self.pair, ask=ask * negative_multiplier, bid=bid
            )
        with self.assertRaises(ValidationError):
            Ticker.objects.create(
                pair=self.pair, ask=ask, bid=bid * positive_multiplier
            )
        with self.assertRaises(ValidationError):
            Ticker.objects.create(
                pair=self.pair, ask=ask, bid=bid * negative_multiplier
            )
        self.assertEqual(Ticker.objects.all().count(), 2)
        # no raise with kwarg
        ticker3 = Ticker(pair=self.pair, ask=ask,
                         bid=bid * negative_multiplier)
        ticker3.save(validate_change=False)
        self.assertEqual(Ticker.objects.all().count(), 3)


class PriceTestCaseTask(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.DISABLE_NON_MAIN_PAIRS = False
        super(PriceTestCaseTask, cls).setUpClass()
        enable_all_pairs()
        cls.factory = Price

    @requests_mock.mock()
    def test_get_rate(self, mock):
        currs = Currency.objects.filter(
            Q(is_crypto=True) | Q(code__in=['EUR', 'USD', 'GBP'])
        ).exclude(code__in=[
            'GNT', 'EOS', 'QTM'
        ])
        self.get_tickers(mock)
        for curr in currs:
            rate_c_usd = self.factory.get_rate(curr, 'USD')
            rate_usd_c = self.factory.get_rate('USD', curr)
            rate_c_eur = self.factory.get_rate(curr, 'EUR')
            rate_eur_c = self.factory.get_rate('EUR', curr)
            self.assertTrue(isinstance(rate_c_usd, Decimal), curr)
            self.assertTrue(isinstance(rate_c_eur, Decimal), curr)
            self.assertTrue(isinstance(rate_usd_c, Decimal), curr)
            self.assertTrue(isinstance(rate_eur_c, Decimal), curr)
            self.assertAlmostEqual(
                rate_c_usd, Decimal('1.0') / rate_usd_c, 8, curr)
            self.assertAlmostEqual(
                rate_c_eur, Decimal('1.0') / rate_eur_c, 8, curr)

    def test_convert_amount(self):
        amount = 1.0
        amount_btc_usd = self.factory.convert_amount(amount, 'BTC', 'USD')
        self.assertTrue(isinstance(amount_btc_usd, Decimal))
        self.assertGreater(amount_btc_usd, Decimal('1.0'))
        amount_usd_btc = self.factory.convert_amount(amount, 'USD', 'BTC')
        self.assertTrue(isinstance(amount_usd_btc, Decimal))
        self.assertLess(amount_usd_btc, Decimal('1.0'))
        amount_doge_doge = self.factory.convert_amount(amount, 'DOGE', 'DOGE')
        self.assertTrue(isinstance(amount_doge_doge, Decimal))
        self.assertEqual(amount_doge_doge, Decimal('1.0'))

    @patch('ticker.models.Price._get_currency')
    def test_eur_usd_amounts_cache(self, get_currency):
        price = Price.objects.filter(pair__name='BTCETH').last()
        get_currency.return_value = Currency.objects.first()
        methods = ['rate_btc', 'rate_eur', 'rate_usd']
        for i, method in enumerate(methods):
            for _ in range(10):
                getattr(price, method)
            self.assertEqual(get_currency.call_count, 2 * (i + 1))

        call_count = get_currency.call_count
        now = datetime.now() + timedelta(seconds=settings.TICKER_INTERVAL + 1)
        with freeze_time(now):
            for i, method in enumerate(methods):
                getattr(price, method)
                self.assertEqual(
                    get_currency.call_count, 2 * (i + 1) + call_count)


class DiscountTestCase(OrderBaseTestCase):

    @requests_mock.mock()
    def test_discount(self, mock):
        pair = Pair.objects.get(name='BTCLTC')
        pair_reverse = pair.reverse_pair
        ltc = pair.quote
        ltc.ticker = 'bittrex'
        ltc.save()
        for p in Pair.objects.exclude(pk__in=[pair.pk, pair_reverse.pk]):
            p.disable_ticker = True
            p.save()

        ask = 0.2
        bid = 0.1
        url = 'https://bittrex.com/api/v1.1/public/getticker/?market=BTC-LTC'
        resp_text = '{{"success":true,"message":"","result":{{"Bid":' \
                    '{bid},"Ask":{ask},"Last":{ask}}}}}'.format(ask=ask,
                                                                bid=bid)
        mock.get(
            url,
            text=resp_text
        )
        mock.get(BittrexAdapter.BASE_URL + 'getmarkets',
                 text=bittrex_market_resp)
        get_all_tickers_force()
        btcltc_price = pair.latest_price
        ltcbtc_price = pair_reverse.latest_price
        discount = FeeDiscount.objects.create(
            name='Much Discount',
            discount_part=Decimal('0.5'),
            active=True
        )
        get_all_tickers_force()
        btcltc_price_discount = pair.latest_price
        ltcbtc_price_discount = pair_reverse.latest_price
        self.assertLess(
            btcltc_price_discount.ticker.ask,
            btcltc_price.ticker.ask
        )
        self.assertLess(
            ltcbtc_price_discount.ticker.ask,
            ltcbtc_price.ticker.ask
        )
        self.assertGreater(
            btcltc_price_discount.ticker.bid,
            btcltc_price.ticker.bid
        )
        self.assertGreater(
            ltcbtc_price_discount.ticker.bid,
            ltcbtc_price.ticker.bid
        )
        for p in [pair, pair_reverse]:
            multip = (Decimal('1') - discount.discount_part)
            self.assertEqual(p.fee_ask * multip, p.fee_ask_current)
            self.assertEqual(p.fee_bid * multip, p.fee_bid_current)
