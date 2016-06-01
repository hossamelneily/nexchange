from django.test import TestCase
from django.core.exceptions import ValidationError
from core.validators import validate_bc
from django.utils import translation
from django.utils import timezone
from django.test import Client
from core.models import Order, Currency
from datetime import timedelta
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import activate
from http.cookies import SimpleCookie
import pytz
from django.conf import settings


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


class ValidateOrderPaymentTestCase(TestCase):

    def setUp(self):
        Currency(code='RUB', name='Rubles').save()
        currency = Currency.objects.get(code='RUB')
        user = User.objects.create_user('+555182459988')

        self.data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': user,
            'admin_comment': 'test Order',
            'unique_reference': '12345'

        }
        pass

    def test_payment_deadline_calculation(self):
        created_on = timezone.now()
        payment_window = 60

        order = Order(**self.data)
        order.payment_window = payment_window
        order.save()

        expected = created_on + timedelta(minutes=payment_window)

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


class OrderPayUntilTestCase(TestCase):

    def setUp(self):
        username = '+555190909898'
        password = '123Mudar'

        activate('en')

        Currency(code='RUB', name='Rubless').save()
        user = User.objects.create_user(username=username, password=password)

        self.client = Client()
        self.client.login(username=username, password=password)

    def test_pay_until_message_is_in_context_and_is_rendered(self):

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

        # Is rendere in template?
        self.assertContains(response, 'id="pay_until_notice"')

    def test_pay_until_message_is_in_correct_time_zone(self):
        # USER_TZ = 'America/Sao_Paulo'
        USER_TZ = 'Asia/Vladivostok'
        self.client.cookies.update(SimpleCookie(
            {'USER_TZ': USER_TZ}))
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

        # Ensure template renders with localtime
        timezone.activate(pytz.timezone(USER_TZ))
        self.assertContains(
            response,
            timezone.localtime(pay_until).strftime("%H:%M%p (%Z)"))

    def test_pay_until_message_uses_settingsTZ_for_invalid_time_zones(self):
        USER_TZ = 'SOMETHING/FOOLISH'

        self.client.cookies.update(SimpleCookie(
            {'USER_TZ': USER_TZ}))
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


class ProfileUpdateTestCase(TestCase):

    def setUp(self):
        username = '+555190909898'
        password = '123Mudar'

        activate('en')

        user = User.objects.create_user(username=username, password=password)

        self.client = Client()
        self.client.login(username=username, password=password)

    def test_can_update_profile(self):
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johndoe@domain.com',
        }

        response = self.client.post(reverse('core.user_profile'), data)
        self.assertEqual(302, response.status_code)  # Redirect after update

        # saved the User instance data
        user = User.objects.get(email=data['email'])
        self.assertEqual(user.profile.first_name, data[
                         'first_name'])  # saved the profile too
        self.assertEqual(user.profile.last_name, data['last_name'])

    def test_phone_verification_with_success(self):
        user = User.objects.first()

        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)

        token = user.profile.sms_token

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})

        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        self.assertJSONEqual('{"status": "OK"}', str(
            response.content, encoding='utf8'),)

        # Ensure profile was enabled
        profile = user.profile
        self.assertFalse(user.profile.disabled)

    def test_phone_verification_fails_with_wrong_token(self):
        user = User.objects.first()
        token = "%sXX" % user.profile.sms_token  # a wrong token

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})
        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)  # succefuly runned
        self.assertJSONEqual('{"status": "NO_MATCH"}',
                             str(  # failure reason indicator
                                 response.content, encoding='utf8'),)
