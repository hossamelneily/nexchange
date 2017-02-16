from decimal import Decimal
import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.utils.translation import activate

from accounts.models import SmsToken
from core.models import Currency, Address, Transaction, Pair
from orders.models import Order
from payments.models import PaymentMethod, PaymentPreference
from ticker.models import Price, Ticker
from copy import deepcopy
import mock
from unittest.mock import patch


class UserBaseTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        with patch('core.signals.allocate_wallets.allocate_wallets'):
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
        with patch('core.signals.allocate_wallets.allocate_wallets'):
            self.user, created = \
                User.objects.get_or_create(username=self.username)
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
        'pair.json',
        'payment_method.json',
        'payment_preference.json'
    ]
    PRICE_BUY_RUB = 36000
    PRICE_BUY_USD = 600
    PRICE_BUY_EUR = 500

    PRICE_SELL_RUB = 30000
    PRICE_SELL_USD = 500
    PRICE_SELL_EUR = 400

    RATE_EUR = 70.00

    @classmethod
    def setUpClass(cls):
        super(OrderBaseTestCase, cls).setUpClass()

        price_api_mock = mock.Mock()
        price_api_mock.return_value = None
        mock.patch.object(Price, 'get_eur_rate', price_api_mock)

        cls.RUB = Currency.objects.get(code='RUB')

        cls.USD = Currency.objects.get(code='USD')

        cls.EUR = Currency.objects.get(code='EUR')

        cls.BTC = Currency.objects.get(code='BTC')

        cls.BTCRUB = Pair.objects.get(name='BTCRUB')
        cls.BTCUSD = Pair.objects.get(name='BTCUSD')
        cls.BTCEUR = Pair.objects.get(name='BTCEUR')

        ticker_rub = Ticker(
            pair=cls.BTCRUB,
            ask=OrderBaseTestCase.PRICE_BUY_RUB,
            bid=OrderBaseTestCase.PRICE_SELL_RUB
        )
        ticker_rub.save()

        ticker_usd = Ticker(
            pair=cls.BTCUSD,
            ask=OrderBaseTestCase.PRICE_BUY_USD,
            bid=OrderBaseTestCase.PRICE_SELL_USD
        )
        ticker_usd.save()

        ticker_eur = Ticker(
            pair=cls.BTCEUR,
            ask=OrderBaseTestCase.PRICE_BUY_EUR,
            bid=OrderBaseTestCase.PRICE_SELL_EUR
        )
        ticker_eur.save()

        cls.price_rub = Price(pair=cls.BTCRUB, ticker=ticker_rub)
        cls.price_rub.save()

        cls.price_usd = Price(pair=cls.BTCUSD, ticker=ticker_usd)
        cls.price_usd.save()

        cls.price_eur = Price(pair=cls.BTCEUR, ticker=ticker_eur)
        cls.price_eur.save()

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


class WalletBaseTestCase(OrderBaseTestCase):
    fixtures = [
        'currency.json',
        'pair.json',
        'payment_method.json',
        'payment_preference.json',
    ]

    @classmethod
    def setUpClass(cls):
        with patch('core.signals.allocate_wallets.allocate_wallets'):
            u, created = User.objects.get_or_create(
                username='onit',
                email='weare@onit.ws'
            )
            # ensure staff status, required for tests
            u.is_staff = True
            u.save()
        super(WalletBaseTestCase, cls).setUpClass()

    def setUp(self):
        super(WalletBaseTestCase, self).setUp()
        # look at:
        # nexchange/tests/fixtures/transaction_history.xml self.order_data
        # matches first transaction from the XML file
        okpay_pref = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method__name__icontains='okpay'
        ).first()

        payeer_pref = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method__name__icontains='payeer'
        ).first()

        self.okpay_order_data = {
            'amount_quote': 85.85,
            'amount_base': Decimal(0.01),
            'pair': self.BTCEUR,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '12345',
            'payment_preference': okpay_pref,
        }
        self.payeer_order_data = deepcopy(self.okpay_order_data)
        self.payeer_order_data['payment_preference'] = payeer_pref

        self.okpay_order_data_address = deepcopy(self.okpay_order_data)
        addr = Address(address='A555B', user=self.user)
        addr.save()
        self.okpay_order_data_address['withdraw_address'] = addr

        self.payeer_order_data_address = deepcopy(
            self.okpay_order_data_address)
        self.payeer_order_data_address['payment_preference'] = payeer_pref


class TransactionImportBaseTestCase(OrderBaseTestCase):

    def setUp(self):
        super(TransactionImportBaseTestCase, self).setUp()
        self._read_fixture()
        self.address = Address(
            name='test address',
            address=self.wallet_address,
            currency=self.BTC,
            user=self.user,
            type=Address.DEPOSIT
        )
        self.address.save()
        self.url = 'http://btc.blockr.io/api/v1/address/txs/{}'.format(
            self.wallet_address
        )
        self.order = Order(
            order_type=Order.SELL,
            amount_base=Decimal(str(self.amounts[self.status_ok_list_index])),
            pair=self.BTCEUR,
            user=self.user,
            status=Order.INITIAL
        )
        self.order.save()
        self.unique_ref = self.order.unique_reference

    def _read_fixture(self):
        cont_path = 'nexchange/tests/fixtures/blockr/address_transactions.json'
        with open(cont_path) as f:
            self.blockr_response = f.read().replace('\n', '').replace(' ', '')
            self.wallet_address = json.loads(self.blockr_response)['data'][
                'address'
            ]
            txs = json.loads(self.blockr_response)['data']['txs']
            self.amounts = [tx['amount'] for tx in txs]
            self.tx_ids = [tx['tx'] for tx in txs]
        self.status_ok_list_index = 0
        self.status_bad_list_index = 1

    def base_test_create_transactions_with_task(self, mock_request,
                                                run_method):
        mock_request.get(self.url, text=self.blockr_response)
        status_ok_list_index = 0
        status_bad_list_index = 1
        run_method()
        tx_ok = Transaction.objects.filter(
            tx_id=self.tx_ids[status_ok_list_index]
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created if order is found!'
        )
        order = Order.objects.get(unique_reference=self.unique_ref)
        self.assertTrue(
            order.status == Order.PAID,
            'Order should be marked as paid after transaction import'
        )
        tx_bad = Transaction.objects.filter(
            tx_id=self.tx_ids[status_bad_list_index]
        )
        self.assertEqual(
            len(tx_bad), 0,
            'Transaction must not be created if order is not found!'
        )
        run_method()
        tx_ok = Transaction.objects.filter(
            tx_id=self.tx_ids[status_ok_list_index]
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created only one time!'
        )
