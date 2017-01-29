from decimal import Decimal

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.utils.translation import activate

from accounts.models import SmsToken
from core.models import Currency, Address
from orders.models import Order
from payments.models import PaymentMethod, PaymentPreference
from ticker.models import Price
import mock


class UserBaseTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        User.objects.get_or_create(
            username='onit',
            email='weare@onit.ws',
        )
        super(UserBaseTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        u = User.objects.get(username='onit')
        # soft delete hack
        u.delete()
        super(UserBaseTestCase, cls).tearDownClass()

    def setUp(self):
        self.logout_url = reverse('accounts.logout')
        self.username = '+491628290463'
        self.password = '123Mudar'
        self.data = \
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@onit.ws',
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
        super(UserBaseTestCase, self).setUp()


class OrderBaseTestCase(UserBaseTestCase):
    fixtures = [
        'currency.json',
        'payment_method.json',
        'payment_preference.json'
    ]
    PRICE_BUY_RUB = 36000
    PRICE_BUY_USD = 600

    PRICE_SELL_RUB = 30000
    PRICE_SELL_USD = 500

    RATE_EUR = 70.00

    @classmethod
    def setUpClass(cls):
        super(OrderBaseTestCase, cls).setUpClass()

        price_api_mock = mock.Mock()
        price_api_mock.return_value = None
        mock.patch.object(Price, 'get_eur_rate', price_api_mock)

        cls.RUB = Currency.objects.get(code='RUB')
        cls.RUB.save()

        cls.USD = Currency.objects.get(code='USD')
        cls.USD.save()

        cls.EUR = Currency.objects.get(code='EUR')

        cls.ticker_buy = \
            Price(type=Price.BUY,
                  price_rub=OrderBaseTestCase.PRICE_BUY_RUB,
                  price_usd=OrderBaseTestCase.PRICE_BUY_USD,
                  rate_eur=Decimal(OrderBaseTestCase.RATE_EUR))

        cls.ticker_buy.save()

        cls.ticker_sell = \
            Price(type=Price.SELL,
                  price_rub=OrderBaseTestCase.PRICE_SELL_RUB,
                  price_usd=OrderBaseTestCase.PRICE_SELL_USD,
                  rate_eur=Decimal(OrderBaseTestCase.RATE_EUR))

        cls.ticker_sell.save()

    @classmethod
    def create_order(cls, user):
        cls.setUpClass()

        payment_method = PaymentMethod.objects.first()

        if payment_method is None:
            method_data = {
                'bin': 426101,
                'fee': 0.0,
                'is_slow': 0,
                'name': 'Alpha Bank Visa'
            }
            payment_method = PaymentMethod(**method_data)
            payment_method.save()

        pref_data = {
            'user': user,
            'identifier': str(payment_method.bin),
            'comment': 'Just testing'
        }
        pref = PaymentPreference(**pref_data)
        pref.save()
        pref.currency.add(cls.USD)

        address = Address(
            address='17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j',
            user=user
        )
        address.save()

        """Creates an order"""
        data = {
            'amount_cash': Decimal(306.85),
            'amount_btc': Decimal(1.00),
            'currency': cls.USD,
            'user': user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'withdraw_address': address,
            'payment_preference': pref
        }

        order = Order(**data)
        order.full_clean()  # ensure is initially correct
        order.save()

        return order
