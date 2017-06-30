from django.test import TestCase
from core.tests.base import OrderBaseTestCase
from core.models import AddressReserve, Currency
from core.common.models import UniqueFieldMixin


class ValidateUniqueFieldMixinTestCase(TestCase):

    def test_detects_uniqe_value_colision(self):

        unq = UniqueFieldMixin.gen_unique_value(
            lambda x: 'A' * x,
            lambda x: 1 if x == 'A' else 0,
            1
        )

        self.assertEqual(unq, 'AA')


class CurrencyTestCase(OrderBaseTestCase):

    def setUp(self):
        super(CurrencyTestCase, self).setUp()
        self.currency = self.USD

    def test_find_currency_by_natural_key(self):
        natural_key = self.currency.natural_key()
        currency = Currency.objects.get_by_natural_key(natural_key)
        self.assertEqual(currency, self.currency)

    def test_print_currency_name(self):
        self.assertEqual(str(self.currency), 'USD')


class AddressReserveTest(OrderBaseTestCase):

    def create_card(self):

        self.data = {
            'card_id': 'ade869d8-7913-4f67-bb4d-72719f0a2be0',
            'address': '145ZeN94MAtTmEgvhXEch3rRgrs7BdD2cY',
            'currency': self.USD,
            'user': self.user,
        }
        AddressReserves = AddressReserve.objects.create(**self.data)
        return AddressReserves

    def test_AddressReserves_creation(self):
        c = self.create_card()
        self.assertTrue(isinstance(c, AddressReserve))
