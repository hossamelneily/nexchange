from django.test import TestCase

from core.common.models import UniqueFieldMixin
from core.models import Currency
from core.tests.base import OrderBaseTestCase


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
