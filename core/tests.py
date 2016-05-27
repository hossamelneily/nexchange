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


class PlaceOrderTestCase(TestCase):

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
            'wallet': 'what goes here?',
            'unique_reference': '12345',
            'withdraw_address': None
        }

    def tearDown(self):
        data = None

    def test_can_place_order_with_good_address(self):
        withdraw_address = '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'
        self.data['withdraw_address'] = withdraw_address

        order = Order(**self.data)
        order.full_clean()  # ensure validators run
        order.save()

        fetch_order = Order.objects.get(withdraw_address=withdraw_address)
        self.assertIsInstance(fetch_order, Order)

    def test_cannot_place_order_with_bad_address(self):
        self.data['withdraw_address'] = '1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i'
        order = Order(**self.data)

        with self.assertRaises(ValidationError):
            order.full_clean()  # ensure validators run

    def test_can_place_order_without_address(self):
        order = Order(**self.data)
        order.full_clean()  # ensure validators run
        order.save()

        fetch_order = Order.objects.filter(withdraw_address=None).count()
        self.assertEqual(fetch_order, 1)


class UpdateWithdrawAddressTestCase(TestCase):

    def setUp(self):
        """Create user and authenticate request"""
        username = '+555190909898'
        password = '123Mudar'
        user = User.objects.create_user(username=username, password=password)
        self.client = Client()
        self.client.login(username=username, password=password)

        translation.deactivate_all()
        translation.activate('en')

        """Creates an order"""
        currency = Currency(code='RUB', name='Rubless')
        currency.save()

        data = {
            'amount_cash': 30674.85,
            'amount_btc': 1,
            'currency': currency,
            'user': user,
            'admin_comment': 'test Order',
            'wallet': 'what goes here?',
            'unique_reference': '12345',
            'withdraw_address': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j'
        }

        order = Order(**data)
        order.full_clean()  # ensure is initially correct
        order.save()
        self.order = order

        # URL where to POST
        pk = self.order.pk
        self.url = reverse('core.update_withdraw_address', kwargs={'pk': pk})

    def test_forbiden_to_update_other_users_orders(self):
        username = '+555190909100'
        password = '321Changed'
        user = User.objects.create_user(username=username, password=password)
        client = Client()
        client.login(username=username, password=password)

        response = client.post(self.url, {
            'pk': self.order.pk,
            'value': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', })

        self.assertEqual(403, response.status_code)

    def test_sucess_to_update_withdraw_adrress(self):
        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', })

        self.assertJSONEqual('{"status": "OK"}', str(
            response.content, encoding='utf8'),)

    def test_error_to_update_withdraw_adrress_with_invalida_data(self):
        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': 'invalid data', })

        expected = '{"status": "ERR", "msg": "invalid data ' + \
            'has invalid characters for a valid bit coin address"}'

        self.assertJSONEqual(expected, str(response.content, encoding='utf8'),)

    def test_forbiden_to_update_frozen_orders(self):
        self.order.is_paid = True
        self.order.save()

        response = self.client.post(self.url, {
            'pk': self.order.pk,
            'value': '17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j', })

        self.assertEqual(403, response.status_code)


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
            'wallet': 'what goes here?',
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
