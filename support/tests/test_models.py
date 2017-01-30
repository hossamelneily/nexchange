from decimal import Decimal

from core.tests.base import OrderBaseTestCase
from orders.models import Order
from support.models import Support


class SupportTestModelUser(OrderBaseTestCase):

    def setUp(self):

        super(SupportTestModelUser, self).setUp()
        currency = self.RUB

        self.data = {
            'amount_cash': Decimal(30674.85),
            'amount_btc': Decimal(1.00),
            'currency': currency,
            'user': self.user,
            'admin_comment': 'tests Order'
        }

        self.order = Order(**self.data)
        self.order.save()

    def create_support(self):

        self.data = {
            'name': 'TestSupport',
            'user': self.user,
            'order': self.order,
            'email': 'johndoe@domain.com',
            'telephone': '123 000 00 00',
            'subject': 'Test case',
            'message': 'this is only a test'
        }
        support = Support.objects.create(**self.data)
        return support

    def test_support_creation(self):
        s = self.create_support()
        self.assertTrue(isinstance(s, Support))
        self.assertEqual(s.__str__(), s.name)
