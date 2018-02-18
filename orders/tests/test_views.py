import json
from datetime import timedelta
from decimal import Decimal
from http.cookies import SimpleCookie
from unittest import mock, skip

import pytz
import requests_mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Profile
from core.models import Address, Currency
from core.tests.base import OrderBaseTestCase
from core.tests.utils import data_provider
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from ticker.tests.base import TickerBaseTestCase
from verification.models import Verification


class OrderSetAsPaidTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderSetAsPaidTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.save()
        self.data = {
            'amount_quote': Decimal(30674.85),
            'amount_base': Decimal(1.00),
            'pair': self.BTCRUB,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345'
        }
        self.order = Order(**self.data)
        self.order.save()

        self.payment_method = PaymentMethod(
            name='Internal Test',
            is_internal=True
        )
        self.payment_method.save()

        self.pref = PaymentPreference(
            payment_method=self.payment_method,
            user=self.order.user,
            identifier='InternalTestIdentifier'
        )
        self.pref.save()

        self.payment = Payment(
            payment_preference=self.pref,
            amount_cash=self.order.amount_quote,
            order=self.order,
            currency=self.RUB,
            user=self.order.user
        )
        self.payment.save()

        self.url = reverse('orders.confirm_payment',
                           kwargs={'pk': self.order.pk})

    def tearDown(self):
        super(OrderSetAsPaidTestCase, self).tearDown()
        # Purge
        Order.objects.all().delete()

    def test_cannot_set_as_paid_if_has_no_withdraw_address(self):
        response = self.client.post(self.url, {'paid': 'true'})
        self.assertEqual(403, response.status_code)

        self.assertEquals(
            response.content,
            b'An order can not be set as paid without a withdraw address')

    @skip('DO NOT merge till fix')
    def test_can_set_as_paid_if_has_withdraw_address(self):
        # Creates an withdraw address fro this user
        address = Address(
            user=self.user, type='W',
            address='17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j')
        address.save()

        self.order.withdraw_address = address
        self.order.save()

        # Set Order as Paid
        response = self.client.post(self.url, {'paid': 'true'})
        expected_dict = {
            "frozen": None,
            "paid": True,
            "status": "OK"
        }
        expected = json.dumps(expected_dict)
        actual = str(response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)

    @skip('DO NOT MERGE TILL FIX')
    def test_can_set_as_paid_if_has_withdraw_address_internal(self):
        # Creates an withdraw address fro this user
        address = Address(
            user=self.user, type='W',
            address='17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j')
        address.save()

        self.order.withdraw_address = address
        self.order.save()

        # Set Order as Paid
        response = self.client.post(self.url, {'paid': 'true'})
        expected_dict = {"frozen": True, "paid": True, "status": "OK"}
        expected = json.dumps(expected_dict)
        actual = str(
            response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)


class OrderPayUntilTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderPayUntilTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.save()

    def test_pay_until_message_is_in_context_and_is_rendered(self):
        params = {
            'pair': 'BTCRUB'
        }
        response = self.client.post(
            reverse('orders.add_order', kwargs=params),
            {
                'amount-cash': '31000',
                'currency_from': 'RUB',
                'amount-coin': '1',
                'currency_to': 'BTC',
                'user': self.user,
            }
        )

        order = Order.objects.filter(amount_base=1, pair__name='BTCRUB').last()
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        # Should be saved if HTTP200re
        self.assertEqual(200, response.status_code)

        # Does context contains the atribute, with correct value?
        self.assertEqual(pay_until, response.context['pay_until'])

        # Is rendere in template?
        self.assertContains(response, 'id="pay_until_notice"')

    def test_pay_until_message_is_in_correct_time_zone(self):
        params = {
            'pair': 'BTCEUR'
        }
        user_tz = 'Asia/Vladivostok'
        self.client.cookies.update(SimpleCookie(
            {'USER_TZ': user_tz}))
        response = self.client.post(
            reverse('orders.add_order', kwargs=params),
            {
                'amount-cash': '31000',
                'currency_from': 'EUR',
                'amount-coin': '1',
                'currency_to': 'BTC',
                'user': self.user,
            }
        )

        order = Order.objects.filter(amount_base=1, pair__name='BTCEUR').last()
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
        params = {
            'pair': 'BTCRUB'
        }
        self.client.cookies.update(SimpleCookie(
            {'user_tz': user_tz}))
        response = \
            self.client.post(
                reverse('orders.add_order', kwargs=params), {
                    'amount-cash': '31000',
                    'currency_from': 'RUB',
                    'amount-coin': '1',
                    'currency_to': 'BTC'}
            )

        order = Order.objects.filter(amount_base=1, pair__name='BTCRUB').last()
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


class UpdateWithdrawAddressTestCase(TickerBaseTestCase):

    def setUp(self):
        super(UpdateWithdrawAddressTestCase, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.save()

        PaymentMethod.objects.all().delete()

        method_data = {
            'bin': 426101,
            'is_slow': 0,
            'name': 'Alpha Bank Visa'
        }
        payment_method = PaymentMethod(**method_data)
        payment_method.save()

        pref_data = {
            'user': self.user,
            'identifier': str(payment_method.bin),
            'comment': 'Just testing'
        }
        pref = PaymentPreference(**pref_data)
        pref.save()
        pref.currency.add(self.USD)
        pref.save()

        """Creates an order"""
        data = {
            'amount_quote': Decimal(30674.85),
            'amount_base': Decimal(1.00),
            'pair': self.BTCUSD,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': pref
        }

        order = Order(**data)
        # TODO: patch and uncomment
        # order.full_clean()  # ensure is initially correct
        order.save()
        self.order = order
        pk = self.order.pk
        self.url = reverse('orders.update_withdraw_address', kwargs={'pk': pk})
        self.url_create_withdraw = reverse('accounts.create_withdraw_address',
                                           kwargs={'order_pk': pk})

        self.addr_data = {
            'type': 'W',
            'name': 'addr1',
            'address': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            'currency': self.BTC

        }

        self.addr_data2 = {
            'type': 'W',
            'name': 'RedAndWhite',
            'address': '1MwvS1idEevZ5gd428TjL3hB2kHaBH9WTL',
            'currency': self.BTC

        }
        self.addr = Address(**self.addr_data)
        self.addr.user = self.user
        self.addr.save()

        # The 'other' address for the Transaction
        with requests_mock.mock() as m:
            self.get_tickers(m)
            self.user, created = \
                User.objects.get_or_create(username='Address von Monitor')
            self.user.save()
            self.profile = Profile(user=self.user)
            self.profile.save()
            self._mock_cards_reserve(m)
            user, created = User.objects.get_or_create(
                username='onit',
                email='weare@onit.ws',
            )
            self._create_order(user=user)
        addr2 = Address(**self.addr_data2)
        addr2.user = user
        addr2.save()

    def test_forbiden_to_update_other_users_orders(self):
        username = '+555190909100'
        password = '321Changed'

        User.objects.create_user(username=username, password=password)

        client = self.client
        client.login(username=username, password=password)
        response = client.post(self.url, {
            'pk': self.order.pk,
            'value': self.addr.pk})

        self.assertEqual(403, response.status_code)
        self.client.logout()

    def test_sucess_to_update_withdraw_adrress(self):
        self.order = Order.objects.filter(
            pair__base__code='BTC', withdraw_address__isnull=True).first()
        self.client.login(username=self.user.username, password='password')
        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': self.addr.pk,
        })

        expected = '{"status": "OK"}'
        actual = str(response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)
        self.order.refresh_from_db()
        self.assertEqual(self.order.withdraw_address, self.addr)

    def test_throw_error_for_invalid_withdraw_adrress(self):
        response = self.client.post(
            self.url, {'pk': self.order.pk, 'value': 50})

        self.assertEqual(b'Invalid address provided', response.content)

    @data_provider(lambda: (
        (True,),
        (False,),
    ))
    def test_throw_error_not_verified_user(self, required_verification):
        order = Order.objects.filter(
            payment_preference__isnull=False).first()
        user = order.user
        pm = order.payment_preference.payment_method
        pm.required_verification_buy = required_verification
        pm.save()
        verifications = user.verification_set.all()
        status_keys = ['id_status', 'util_status']
        for key in status_keys:
            for ver in verifications:
                setattr(ver, key, Verification.REJECTED)
                ver.save()
            response = self.client.post(
                self.url, {'pk': order.pk, 'value': self.addr.pk})
            if required_verification:
                response_create = self.client.post(
                    self.url_create_withdraw,
                    {'order_pk': order.pk, 'value': self.addr.address}
                )

                expected_msg = \
                    b'You need to be a verified user to set withdrawal address'
                self.assertIn(expected_msg, response_create.content)
            if not required_verification:
                expected_msg = b'"status": "OK"'
            self.assertIn(expected_msg, response.content)
            setattr(ver, key, Verification.OK)
            ver.save()
            order.withdraw_address = None
            order.save()
            if not required_verification:
                break

    @mock.patch('orders.task_summary.buy_order_release_by_reference_invoke')
    def release_on_first_withdraw_address_change(self, invoke):
        self.client.login(username=self.user.username, password='password')
        self.order.status = Order.PAID
        self.order.save()

        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': self.addr.pk,
        })

        expected = '{"status": "OK"}'
        actual = str(response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)
        self.order.refresh_from_db()
        self.assertEqual(self.order.withdraw_address, self.addr)
        self.assertEquals(1, invoke.call_count)
        invoke.assert_called_once_with([self.order.payment_set.first().pk])

    @mock.patch('orders.task_summary.buy_order_release_by_reference_invoke')
    def dont_release_on_first_withdraw_address_change_not_paid(self, invoke):
        self.client.login(username=self.user.username, password='password')
        self.order.status = Order.PAID_UNCONFIRMED
        self.order.save()
        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': self.addr.pk,
        })

        expected = '{"status": "OK"}'
        actual = str(response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)
        self.order.refresh_from_db()
        self.assertEqual(self.order.withdraw_address, self.addr)
        self.assertEquals(0, invoke.call_count)

    @mock.patch('orders.task_summary.buy_order_release_by_reference_invoke')
    def dont_release_on_first_withdraw_address_change_not_paid2(self, invoke):
        self.client.login(username=self.user.username, password='password')
        self.order.status = Order.PAID_UNCONFIRMED
        self.order.save()
        response = None
        for i in range(2):
            response = self.client.post(self.url, {
                'pk': self.order.pk,
                'value': self.addr.pk,
            })

        expected = '{"status": "OK"}'
        actual = str(response.content, encoding='utf8')
        self.assertJSONEqual(expected,
                             actual,)
        self.order.refresh_from_db()
        self.assertEqual(self.order.withdraw_address, self.addr)
        self.assertEquals(0, invoke.call_count)


class OrderIndexOrderTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderIndexOrderTestCase, self).setUp()

    def test_redirect_login_for_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('orders.orders_list'))
        self.assertEqual(302, response.status_code)

        success = self.client.login(
            username=self.username, password=self.password)
        self.assertTrue(success)

    def test_renders_empty_list_of_user_orders(self):
        Order.objects.filter(user=self.user).delete()
        with self.assertTemplateUsed('orders/orders_list.html'):
            response = self.client.get(reverse('orders.orders_list'))
            self.assertEqual(200, response.status_code)
            self.assertEqual(0, len(response.context['orders']))

    @skip("causes failures, needs to be migrated")
    def test_renders_non_empty_list_of_user_orders(self):
        with self.assertTemplateUsed('orders/orders_list.html'):
            response = self.client.get(reverse('orders.add_order'))
            self.assertEqual(200, response.status_code)
            self.assertEqual(1, len(response.context['orders'].object_list))

        Order.objects.filter(user=self.user).delete()

    @skip("causes failures, needs to be migrated")
    def test_filters_list_of_user_orders(self):
        date = timezone.now().strftime("%Y-%m-%d")
        response = self.client.post(
            reverse('orders.add_order'), {
                'date': date})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.context['orders'].object_list))

        date = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.post(
            reverse('orders.add_order'), {
                'date': date})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.context['orders'].object_list))

        response = self.client.post(
            reverse('orders.add_order'), {
                'date': None})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.context['orders'].object_list))

        Order.objects.filter(user=self.user).delete()


class TestGetPrice(TickerBaseTestCase):

    def tearDown(self):
        super(TestGetPrice, self).tearDown()
        # Purge
        Order.objects.all().delete()

    def test_return_correct_quote(self):
        client = APIClient()
        amount_base = 0.005
        pair_name = 'BTCEUR'
        get_price_quote = client.get(
            '/en/api/v1/get_price/{}/'.format(pair_name),
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
            '/en/api/v1/get_price/{}/'.format(pair_name),
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
        res = client.get('/en/api/v1/get_price/BTCEUR/',
                         data={'amount_base': 0.005})
        self.assertEqual(res.status_code, 200)
        orders_after = Order.objects.count()
        self.assertEqual(orders_before, orders_after)
