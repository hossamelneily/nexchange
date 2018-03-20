from core.tests.base import OrderBaseTestCase
from core.models import Pair
from orders.serializers import CreateOrderSerializer
from django.core.exceptions import ValidationError


class OrderSerializerTestCase(OrderBaseTestCase):

    def setUp(self):
        super(OrderSerializerTestCase, self).setUp()
        self.create_ser = CreateOrderSerializer()
        self.pair = Pair.objects.get(name='LTCBTC')
        self.pair.disabled = False
        self.pair.save()
        self.address = 'LhkiJT2HXvUbYNN4QsK9b3vb5Ey6SKtZ6f'
        self.data = {
            'pair': {'name': self.pair.name},
            'withdraw_address': {'address': self.address},
            'amount_base': 111
        }

    def test_create_validator_disabled_pair(self):
        self.pair.disabled = True
        self.pair.save()
        with self.assertRaises(ValidationError):
            self.create_ser.validate(self.data)

    def test_create_validator_no_amount(self):
        self.data.pop('amount_base')
        with self.assertRaises(ValidationError):
            self.create_ser.validate(self.data)

    def test_ok(self):
        res = self.create_ser.validate(self.data)
        self.assertEqual(res, self.data)
