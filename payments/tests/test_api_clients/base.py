from core.tests.base import OrderBaseTestCase
from payments.api_clients.card_pmt import CardPmtAPIClient
from payments.api_clients.sofort import SofortAPIClient
from django.core.validators import URLValidator
from core.tests.utils import read_fixture
from orders.models import Order
from payments.models import PaymentPreference
from django.conf import settings
from time import time


class BaseCardPmtAPITestCase(OrderBaseTestCase):

    def setUp(self):
        super(BaseCardPmtAPITestCase, self).setUp()
        self.order_data = {
            'amount_base': 0.1,
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


class BaseSofortAPITestCase(OrderBaseTestCase):

    def setUp(self):
        super(BaseSofortAPITestCase, self).setUp()
        self.sofort_pref = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method__name__icontains='sofort'
        ).first()
        self.order_data = {
            'amount_base': 0.1,
            'pair': self.BTCEUR,
            'user': self.user,
            'payment_preference': self.sofort_pref,
        }
        self.order = Order.objects.create(**self.order_data)
        self.api_client = SofortAPIClient()
        self.transaction_history_empty = read_fixture(
            'payments/tests/fixtures/sofort/transaction_history_empty.xml'
        )
        self.transaction_empty = read_fixture(
            'payments/tests/fixtures/sofort/transaction_empty.xml'
        )

    def create_transaction_xml(self, project_id=settings.SOFORT_PROJECT_ID,
                               transaction_id=str(time()), amount='10.00',
                               currency='EUR', order_id='54321',
                               sender_name='Sir Buyalot',
                               iban='DE86000000002345678902'):
        transaction = self.transaction_empty.format(
            project_id=project_id,
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
            order_id=order_id,
            sender_name=sender_name,
            iban=iban,
        )
        return transaction

    def mock_transaction_history(self, mock, transactions_xml, status=200):
        transaction_history = self.transaction_history_empty.format(
            transactions=transactions_xml
        )
        mock.post(self.api_client.url, text=transaction_history,
                  status_code=status)
