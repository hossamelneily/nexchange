from core.tests.base import OrderBaseTestCase
from payments.api_clients.card_pmt import CardPmtAPIClient
from django.core.validators import URLValidator
from core.tests.utils import read_fixture
from orders.models import Order


class BaseCardPmtAPITestCase(OrderBaseTestCase):

    def setUp(self):
        super(BaseCardPmtAPITestCase, self).setUp()
        self.order_data = {
            'amount_base': 1.00,
            'pair': self.BTCUSD,
            'user': self.user,
        }
        self.order = Order.objects.create(**self.order_data)
        self.required_params_dict = {
            'amount': str(self.order.amount_quote),
            'currency': self.order.pair.quote.code,
            'ccn': '5393932585574906',
            'ccexp': '0219',
            'cvv': '123',
            'orderid': self.order.unique_reference,
            'desc': 'BUY 0.1 BTC',
            'firstname': 'John',
            'lastname': 'Smith',
            'country_code': 'US',
            'state_or_province': 'TX',
            'address1': 'Random str 12=2345',
            'address2': 'Area 51',
            'city': 'Dallas',
            'zip': '12345',
            'phone': '37068644145',
            'email': 'test@email.com',
            'ip': '1.1.1.1'
        }
        self.pmt_client = CardPmtAPIClient()
        self.url_validator = URLValidator()
        self.transaction_response_empty = read_fixture(
            'payments/tests/fixtures/card_pmt/transaction_response_empty.html'
        )

    def check_location(self, location, user=None, **kwargs):
        if user is None:
            user = self.user
        self.assertEqual(location.firstname, kwargs['firstname'])
        self.assertEqual(location.lastname, kwargs['lastname'])
        self.assertEqual(location.zip, kwargs['zip'])
        self.assertEqual(location.country, kwargs['country_code'])
        self.assertEqual(location.state, kwargs['state_or_province'])
        self.assertEqual(location.city, kwargs['city'])
        self.assertEqual(location.address1, kwargs['address1'])
        self.assertEqual(location.user, user)
        if 'address2' in kwargs:
            self.assertEqual(location.address2, kwargs['address2'])
