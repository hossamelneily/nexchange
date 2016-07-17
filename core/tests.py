from django.test import TestCase
from django.core.exceptions import ValidationError
from core.validators import validate_bc
from django.utils import timezone
from django.test import Client
from core.models import Order, Currency, SmsToken, Profile, Address,\
    Transaction
from ticker.models import Price
from datetime import timedelta
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import activate
from http.cookies import SimpleCookie
import pytz
import json
import time
from django.conf import settings


def data_provider(fn_data_provider):
    """
    Data provider decorator
    allows another callable to provide the data for the test
    """
    def test_decorator(fn):
        def repl(self):
            for i in fn_data_provider():
                try:
                    fn(self, *i)
                except AssertionError as e:
                    print("Assertion error caught with data set ", i)
                    raise e
        return repl
    return test_decorator


class ValidateBCTestCase(TestCase):

    def setUp(self):
        pass

    def test_validator_recognizes_bad_address(self):
        with self.assertRaises(ValidationError):
            '''valid chars but invalid address'''
            validate_bc('1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i')

        with self.assertRaises(ValidationError):
            validate_bc('invalid chars like l 0 o spaces...')

    def test_validator_recognizes_good_address(self):
        self.assertEqual(None, validate_bc(
            '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'))


class UserBaseTestCase(TestCase):

    def setUp(self):
        self.username = '+555190909898'
        self.password = '123Mudar'
        self.data = \
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'johndoe@domain.com',
            }

        activate('en')

        self.user, created = User.objects.get_or_create(username=self.username)
        self.user.set_password(self.password)
        self.user.save()
        assert isinstance(self.user, User)
        token = SmsToken(user=self.user)
        token.save()
        self.client = Client()
        success = self.client.login(username=self.username,
                                    password=self.password)
        assert success
        super(UserBaseTestCase, self).setUpClass()


class ProfileUpdateTestCase(UserBaseTestCase):

    def test_can_update_profile(self):
        response = self.client.post(reverse('core.user_profile'), self.data)
        # Redirect after update
        self.assertEqual(302, response.status_code)

        # saved the User instance data
        user = User.objects.get(email=self.data['email'])
        self.assertEqual(user.profile.first_name, self.data[
                         'first_name'])  # saved the profile too
        self.assertEqual(user.profile.last_name, self.data['last_name'])

    def test_phone_verification_with_success(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = sms_token.sms_token

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})

        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        self.assertJSONEqual(
            '{"status": "OK"}',
            str(response.content, encoding='utf8'))

        # Ensure profile was enabled
        self.assertFalse(user.profile.disabled)

    def test_phone_verification_fails_with_wrong_token(self):
        # incorrect token
        token = "{}XX".format(SmsToken.get_sms_token())

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})
        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        self.assertJSONEqual('{"status": "NO_MATCH"}',
                             str(
                                 response.content, encoding='utf8'),)


class RegistrationTestCase(TestCase):

    def setUp(self):
        self.data = {
            'phone': '+555190909891',
            'password1': '123Mudar',
            'password2': '123Mudar',
        }
        super(RegistrationTestCase, self).setUp()

    def test_can_register(self):
        response = self.client.post(
            reverse('core.user_registration'), self.data)

        # Redirect is to user profile Page
        self.assertEqual(302, response.status_code)
        self.assertEqual(reverse('core.user_profile'), response.url)

        # Saved data Ok
        user = User.objects.last()
        self.assertEqual(self.data['phone'], user.profile.phone)

    def test_cannot_register_existant_phone(self):

        # Creates first with the phone
        self.client.post(
            reverse('core.user_registration'),
            self.data
        )

        # ensure is created
        self.assertIsInstance(
            Profile.objects.get(phone=self.data['phone']), Profile)

        response = self.client.post(
            reverse('core.user_registration'), self.data)

        self.assertFormError(response, 'profile_form', 'phone',
                             'This phone is already registered.')


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
                  price_rub=OrderPriceGenerationTest.PRICE_BUY_RUB,
                  price_usd=OrderPriceGenerationTest.PRICE_BUY_USD)
        cls.ticker_buy.save()

        cls.ticker_sell = \
            Price(type=Price.SELL,
                  price_rub=OrderPriceGenerationTest.PRICE_SELL_RUB,
                  price_usd=OrderPriceGenerationTest.PRICE_SELL_USD)
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


class OrderValidatePaymentTestCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(OrderValidatePaymentTestCase, self).setUp()
        currency = self.RUB
        self.data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': self.user,
            'admin_comment': 'test Order',

        }

    def test_payment_deadline_calculation(self):
        created_on = timezone.now()
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        expected = created_on + timedelta(minutes=payment_window)
        order.save()
        # ignore ms
        self.assertTrue(abs(expected - order.payment_deadline) <
                        timedelta(seconds=1))

    def test_is_expired_after_payment_deadline(self):
        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        self.assertTrue(order.expired)

    def test_is_not_expired_if_paid(self):

        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.is_paid = True
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        # deadline is in the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # but already paid
        self.assertTrue(order.is_paid)

        # so it's not expired
        self.assertFalse(order.expired)

    def test_is_frozen_if_expired(self):
        order = Order(**self.data)
        order.payment_window = 60  # expires after 1h
        order.save()

        order = Order.objects.last()
        order.created_on = timezone.now() - timedelta(minutes=120)  # 2h ago

        # deadline is in the past
        self.assertTrue(timezone.now() > order.payment_deadline)

        # so it's frozen
        self.assertTrue(order.frozen)

        # even though it's not paid
        self.assertFalse(order.is_paid)

    def test_is_frozen_if_paid(self):
        order = Order(**self.data)
        order.is_paid = True
        order.save()

        order = Order.objects.last()

        # it's paid
        self.assertTrue(order.is_paid)

        # therefore it's frozen
        self.assertTrue(order.frozen)

        # even though deadline is in the future
        self.assertTrue(order.payment_deadline >= timezone.now())

    def test_is_not_frozen_if_is_not_paid_neither_expired(self):
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        order.save()

        order = Order.objects.last()

        # it's not paid
        self.assertFalse(order.is_paid)

        # also it's not expired
        self.assertFalse(order.expired)

        # so it's not frozen
        self.assertFalse(order.frozen)


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

        # TODO: fix this test! 4fdr4fa
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


class OrderPriceGenerationTest(OrderBaseTestCase, UserBaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderPriceGenerationTest, cls).setUpClass()

    def test_auto_set_amount_cash_buy_btc_with_usd(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_USD * amount_btc
        self.order = Order(order_type=Order.BUY, amount_btc=amount_btc,
                           currency=self.USD, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_buy_btc_with_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_BUY_RUB * amount_btc
        self.order = Order(order_type=Order.BUY, amount_btc=amount_btc,
                           currency=self.RUB, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_sell_btc_for_usd(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_USD * amount_btc
        self.order = Order(order_type=Order.SELL, amount_btc=amount_btc,
                           currency=self.USD, user=self.user)
        self.order.save()

        self.assertEqual(self.order.amount_cash, expected)

    def test_auto_set_amount_cash_sell_btc_for_rub(self):
        amount_btc = 2.5
        expected = OrderBaseTestCase.PRICE_SELL_RUB * amount_btc
        self.order = Order(order_type=Order.SELL, amount_btc=amount_btc,
                           currency=self.RUB, user=self.user)
        self.order.save()
        self.assertEqual(self.order.amount_cash, expected)


class OrderUniqueReferenceTestsCase(UserBaseTestCase, OrderBaseTestCase):

    def setUp(self):
        super(OrderUniqueReferenceTestsCase, self).setUp()
        self.data = {
            'amount_cash': 36000,
            'amount_btc': 1,
            'currency': self.RUB,
            'user': self.user,
            'admin_comment': 'test Order',
        }

    def get_data_provider(self, x):
        return lambda:\
            ((lambda data: Order(**data), i) for i in range(x))

    @data_provider(get_data_provider(None, 1000))
    def test_unique_token_creation(self, order_gen, counter):
        order = order_gen(self.data)
        order.save()
        objects = Order.objects.filter(unique_reference=order.unique_reference)
        self.assertEqual(len(objects), 1)
        self.assertIsInstance(counter, int)

    @data_provider(get_data_provider(None, 10000))
    def test_timing_token_creation(self, order_gen, counter):
        max_execution = 0.5
        start = time.time()
        order = order_gen(self.data)
        order.save()
        end = time.time()
        delta = end - start
        self.assertEqual(settings.UNIQUE_REFERENCE_LENGTH,
                         len(order.unique_reference))
        self.assertGreater(max_execution, delta)
        self.assertIsInstance(counter, int)
