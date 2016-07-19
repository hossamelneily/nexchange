from django.test import TestCase
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.conf import settings
from http.cookies import SimpleCookie
from datetime import timedelta
import pytz
import json

from core.models import Order, Currency, Address, Transaction
from ticker.models import Price
from .utils import UserBaseTestCase


class OrderBaseTestCase(TestCase):
    PRICE_BUY_RUB = 36000
    PRICE_BUY_USD = 600
    PRICE_SELL_RUB = 30000
    PRICE_SELL_USD = 500

    @classmethod
    def setUpClass(cls):
        cls.RUB = Currency(code='RUB', name='Rubles')
        cls.RUB.save()
        cls.USD = Currency(code='USD', name='US Dollars')
        cls.USD.save()
        cls.ticker_buy = \
            Price(type=Price.BUY,
                  price_rub=OrderBaseTestCase.PRICE_BUY_RUB,
                  price_usd=OrderBaseTestCase.PRICE_BUY_USD)
        cls.ticker_buy.save()

        cls.ticker_sell = \
            Price(type=Price.SELL,
                  price_rub=OrderBaseTestCase.PRICE_SELL_RUB,
                  price_usd=OrderBaseTestCase.PRICE_SELL_USD)
        cls.ticker_sell.save()
        super(OrderBaseTestCase, cls).setUpClass()


class OrderSetAsPaidTestCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(OrderSetAsPaidTestCase, self).setUp()
        currency = self.RUB

        self.data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': self.user,
            'admin_comment': 'test Order',
            'unique_reference': '12345'
        }
        self.order = Order(**self.data)
        self.order.save()

        self.url = reverse('core.payment_confirmation',
                           kwargs={'pk': self.order.pk})

    def test_cannot_set_as_paid_if_has_no_widthdraw_address(self):
        response = self.client.post(self.url, {'paid': 'true'})
        self.assertEqual(403, response.status_code)

        self.assertEquals(
            response.content,
            b'An order can not be set as paid without a withdraw address')

    def test_can_set_as_paid_if_has_withdraw_address(self):
        # Creates an withdraw address fro this user
        address = Address(
            user=self.user, type='W',
            address='17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j')
        address.save()

        # Creates an Transaction for the Order, using the user Address
        transaction = Transaction(
            order=self.order, address_to=address, address_from=address)
        transaction.save()

        # Set Order as Paid
        response = self.client.post(self.url, {'paid': 'true'})
        expected = {"frozen": True, "paid": True, "status": "OK"}
        self.assertJSONEqual(json.dumps(expected), str(
            response.content, encoding='utf8'),)


class OrderPayUntilTestCase(OrderBaseTestCase, UserBaseTestCase):

    def test_pay_until_message_is_in_context_and_is_rendered(self):
        response = self.client.post(
            reverse('core.order_add'),
            {
                'amount-cash': '31000',
                'currency_from': 'RUB',
                'amount-coin': '1',
                'currency_to': 'BTC',
                'user': self.user,
            }
        )

        order = Order.objects.last()
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        # Should be saved if HTTP200re
        self.assertEqual(200, response.status_code)

        # Does context contains the atribute, with correct value?
        self.assertEqual(pay_until, response.context['pay_until'])

        # Is rendere in template?
        self.assertContains(response, 'id="pay_until_notice"')

    def test_pay_until_message_is_in_correct_time_zone(self):
        user_tz = 'Asia/Vladivostok'
        self.client.cookies.update(SimpleCookie(
            {'USER_TZ': user_tz}))
        response = self.client.post(
            reverse('core.order_add'),
            {
                'amount-cash': '31000',
                'currency_from': 'RUB',
                'amount-coin': '1',
                'currency_to': 'BTC',
                'user': self.user,
            }
        )

        order = Order.objects.last()
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        # Should be saved if HTTP200re
        self.assertEqual(200, response.status_code)

        # Does context contains the atribute, with correct value?
        self.assertEqual(pay_until, response.context['pay_until'])

        # Is rendered in template?
        self.assertContains(response, 'id="pay_until_notice"')

        # Ensure template renders with localtime
        timezone.activate(pytz.timezone(user_tz))
        self.assertContains(
            response,
            timezone.localtime(pay_until).strftime("%H:%M%p (%Z)"))

    def test_pay_until_message_uses_settingsTZ_for_invalid_time_zones(self):
        user_tz = 'SOMETHING/FOOLISH'

        self.client.cookies.update(SimpleCookie(
            {'user_tz': user_tz}))
        response = self.client.post(reverse('core.order_add'), {
            'amount-cash': '31000',
            'currency_from': 'RUB',
            'amount-coin': '1',
            'currency_to': 'BTC'}
        )

        order = Order.objects.last()
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        # Should be saved if HTTP200re
        self.assertEqual(200, response.status_code)

        # Does context contains the atribute, with correct value?
        self.assertEqual(pay_until, response.context['pay_until'])

        # Is rendered in template?
        self.assertContains(response, 'id="pay_until_notice"')

        # Ensure template renders with the timezone defined as default
        timezone.activate(pytz.timezone(settings.TIME_ZONE))
        self.assertContains(response,
                            timezone.localtime(pay_until)
                            .strftime("%H:%M%p (%Z)"))
