from django.test import TestCase
from django.test import Client
from core.models import Order, Currency
from datetime import timedelta
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User


# Create your tests here.


class OrderPayUntilTestCase(TestCase):

    def setUp(self):
        username = '+555190909898'
        password = '123Mudar'

        Currency(code='RUB', name='Russian Rubles').save()
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

        # Should be saved if HTTP200
        self.assertEqual(200, response.status_code)

        # Does context contains the atribute, with correct value?
        self.assertEqual(pay_until, response.context['pay_until'])

        # Is rendere in template?
        self.assertContains(response, 'id="pay_until_notice"')
