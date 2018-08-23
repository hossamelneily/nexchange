from decimal import Decimal

from core.tests.base import OrderBaseTestCase
from core.tests.utils import enable_all_pairs
from orders.models import Order
from support.models import Support
from core.models import Currency


class SupportTestModelUser(OrderBaseTestCase):

    def setUp(self):

        super(SupportTestModelUser, self).setUp()
        enable_all_pairs()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()
        pair = self.BTCRUB

        self.data = {
            'amount_quote': Decimal(30674.85),
            'amount_base': Decimal(1.00),
            'pair': pair,
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
