from decimal import Decimal
import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.utils.translation import activate

from accounts.models import SmsToken
from core.models import Currency, Address, Transaction, Pair
from core.tests.utils import get_ok_pay_mock, split_ok_pay_mock
from orders.models import Order
from payments.models import PaymentMethod, PaymentPreference
from ticker.models import Price, Ticker
from verification.models import Verification
from copy import deepcopy
import mock
import os
from django.conf import settings
import requests_mock
from time import time
import re
from unittest.mock import patch
from random import randint

UPHOLD_ROOT = 'nexchange.api_clients.uphold.Uphold.'
EXCHANGE_ORDER_RELEASE_ROOT = 'orders.tasks.generic.exchange_order_release.' \
                              'ExchangeOrderRelease.'


class UserBaseTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(UserBaseTestCase, self).__init__(*args, **kwargs)
        self.rpc_mock = None

    @classmethod
    def setUpClass(cls):
        User.objects.get_or_create(
            username='onit',
            email='weare@onit.ws',
            is_staff=True
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
        # this is used to identify addresses created by allocate_wallets mock
        self.address_id_pattern = 'addr_id_'
        self._mock_rpc()
        self._mock_uphold()
        self.create_main_user()

        assert isinstance(self.user, User)
        token = SmsToken(user=self.user)
        token.save()
        self.client = Client()
        success = self.client.login(username=self.username,
                                    password=self.password)
        assert success
        super(UserBaseTestCase, self).setUp()

    @patch('orders.models.Order.calculate_quote_from_base')
    def create_main_user(self, convert_cash):
        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            self.user, created = \
                User.objects.get_or_create(username=self.username)
            self.user.set_password(self.password)
            self.user.save()
            Verification(user=self.user,
                         id_status=Verification.OK,
                         util_status=Verification.OK).save()
            convert_cash.return_value = True
            self._create_an_order_for_every_crypto_currency_card(
                self.user, amount_quote='1.1')
    # deprecated

    def _request_card(self, request, context):  # noqa
        post_params = {}
        params = request._request.body.split('&')
        for param in params:
            p = param.split('=')
            post_params.update({p[0]: p[1]})
        currency = post_params['currency']
        card_id = '{}{}'.format(str(time()), randint(1, 999))
        res = (
            '{{"id":"{card_id}", "currency": '
            '"{currency}"}}'.format(currency=currency,
                                    card_id=card_id)
        )
        return res

    def _get_id(self, prefix):
        id = str(time()).split('.')[1]
        rand = randint(0, 999)
        pattern = '{prefix}_{base}{id}{rand}'
        return pattern.format(prefix=prefix,
                              base=self.address_id_pattern,
                              id=id, rand=rand)

    # deprecated
    def _request_address(self, request, context):
        res = '{{"id":"{addr}"}}'.format(
            pattern=self.address_id_pattern,
            addr=self._get_id('addr')
        )
        return res

    def _mock_rpc(self):
        def addr_response(_self, c):
            return {
                'address': self._get_id('addr'),
                'currency': c
            }

        rpc_client_path = 'nexchange.api_clients.rpc.ScryptRpcApiClient.'

        self.rpc_mock_addr = \
            mock.patch(rpc_client_path + 'create_address',
                       new=addr_response)
        self.rpc_mock_addr.start()

        self.rpc_mock_addr.start()

        self.mock_rpc_txs = mock.patch(rpc_client_path + '_get_txs',
                                       lambda _self, *args: [])
        self.mock_rpc_txs.start()

    def _mock_uphold(self):
        uphold_client_path = 'nexchange.api_clients.uphold.UpholdApiClient.'
        self.new_card_mock = mock.patch(
            uphold_client_path + '_new_card',
            new=lambda s, c: {'currency': c, 'id': self._get_id('card')})
        self.new_addr_mock = mock.patch(
            uphold_client_path + '_new_address',
            new=lambda s, c, n: {'id': self._get_id('addr')})

        self.new_addr_mock.start()
        self.new_card_mock.start()

    # deprecated
    def _mock_cards_reserve(self, _mock):
        # renos_coin = Currency.objects.get(code='RNS')
        _mock.post(
            'https://api.uphold.com/v0/me/cards/',
            text=self._request_card
        )
        pattern_addr = re.compile('https://api.uphold.com/v0/me/cards/.+/addresses')  # noqa
        _mock.post(pattern_addr, text=self._request_address)

    def _create_order(self, order_type=Order.BUY,
                      amount_base=0.5, pair_name='ETHLTC',
                      payment_preference=None, user=None, amount_quote=None):
        pair = Pair.objects.get(name=pair_name)
        if user is None:
            user = self.user
        self.order = Order(
            order_type=order_type,
            amount_base=Decimal(str(amount_base)) if amount_base else None,
            pair=pair,
            user=user,
            status=Order.INITIAL,
            amount_quote=Decimal(str(amount_quote)) if amount_quote else None
        )
        if payment_preference is not None:
            self.order.payment_preference = payment_preference
        self.order.save()

    def _create_an_order_for_every_crypto_currency_card(self, user,
                                                        amount_quote=None):
        crypto_currencies = Currency.objects.filter(is_crypto=True).exclude(
            code='RNS')
        crypto_codes = [curr.code for curr in crypto_currencies]
        for code in crypto_codes:
            pair_name = Pair.objects.filter(quote__code=code).first().name
            self._create_order(user=user, pair_name=pair_name,
                               amount_quote=amount_quote)


class OrderBaseTestCase(UserBaseTestCase):
    fixtures = [
        'market.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'country.json',
        'pairs_cross.json',
        'pairs_btc.json',
        'pairs_eth.json',
        'pairs_ltc.json',
        'pairs_rns.json',
        'payment_method.json',
        'payment_preference.json',
        'reserve.json',
        'account.json'
    ]
    PRICE_BUY_RUB = 36000
    PRICE_BUY_USD = 600
    PRICE_BUY_EUR = 500

    PRICE_SELL_RUB = 30000
    PRICE_SELL_USD = 500
    PRICE_SELL_EUR = 400

    RATE_EUR = 70.00

    def setUp(self):
        super(OrderBaseTestCase, self).setUp()
        self.patcher_twilio_send_sms = patch(
            'accounts.api_clients.auth_messages._send_sms')
        self.patcher_twilio_send_sms2 = patch(
            'nexchange.utils._send_sms')
        self.patcher_send_email = patch(
            'accounts.api_clients.auth_messages.send_email')
        self.patcher_send_email2 = patch(
            'nexchange.utils.send_email')
        self._send_sms_patch = self.patcher_twilio_send_sms.start()
        self._send_sms_patch2 = self.patcher_twilio_send_sms2.start()
        self._send_email_patch = self.patcher_send_email.start()
        self._send_email_patch2 = self.patcher_send_email2.start()
        self._send_sms_patch.return_value = \
            self._send_sms_patch2.return_value = 'OK'
        self._send_email_patch.return_value = self._send_email_patch2 = None
        self.patcher_uphold_reserve_txn = patch(
            UPHOLD_ROOT + 'get_transactions'
        )
        self._reserve_txn_uphold = self.patcher_uphold_reserve_txn.start()
        self._reserve_txn_uphold.return_value = {'status': 'completed'}
        pairs = Pair.objects.filter(disabled=True)
        for pair in pairs:
            pair.disabled = False
            pair.disable_ticker = False
            pair.save()

    def tearDown(self):
        super(OrderBaseTestCase, self).tearDown()
        self.patcher_twilio_send_sms.stop()
        self.patcher_twilio_send_sms2.stop()
        self.patcher_send_email.stop()
        self.patcher_send_email2.stop()
        self.patcher_uphold_reserve_txn.stop()
        # self.card.delete()

        # rpc
        self.rpc_mock_addr.stop()
        self.mock_rpc_txs.stop()

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

    def get_uphold_tx(self, currency_code, amount, card_id):
        return {
            'id': 'txapi{}{}'.format(time(), randint(1, 999)),
            'status': 'completed',
            'type': 'deposit',
            'destination': {
                'amount': amount,
                'currency': currency_code,
                'CardId': card_id
            },
            'params': {
                'txid': 'tx{}{}'.format(time(), randint(1, 999))
            }
        }

    def generate_txn_id(self):
        txn_id = 'txid_{}{}'.format(time(), randint(1, 999))
        return txn_id


class WalletBaseTestCase(OrderBaseTestCase):

    @classmethod
    def setUpClass(cls):
        u, created = User.objects.get_or_create(
            username='onit',
            email='weare@onit.ws',
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

        mock = get_ok_pay_mock()
        self.okpay_order_data = {
            'amount_quote': Decimal(split_ok_pay_mock(mock, 'Net')),
            'amount_base': Decimal(0.01),
            'pair': self.BTCEUR,
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': split_ok_pay_mock(mock, 'Comment'),
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
    fixtures = [
        'market.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'pairs_cross.json',
        'pairs_btc.json',
        'pairs_ltc.json',
        'pairs_rns.json',
        'pairs_eth.json',
        'payment_method.json',
        'payment_preference.json',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uphold_import_transactions_empty = None

    def setUp(self):
        super(TransactionImportBaseTestCase, self).setUp()

        self.main_pref = self.okpay_pref = PaymentPreference.objects.get(
            user__is_staff=True,
            payment_method__name__icontains='okpay'
        )

        self.payeer_pref = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method__name__icontains='payeer'
        ).first()

        self.order = Order(
            order_type=Order.SELL,
            amount_base=0.1,
            pair=self.BTCEUR,
            user=self.user,
            status=Order.INITIAL,
            payment_preference=self.main_pref
        )
        with requests_mock.mock() as mock:
            self._mock_cards_reserve(mock)
            self.order.save()

        self.order_modifiers = [
            {'confirmations': self.order.pair.base.min_confirmations},
            {'confirmations': self.order.pair.base.min_confirmations - 1}
        ]

        self._read_fixture()

        self.order.amount_base = \
            Decimal(str(self.amounts[self.status_ok_list_index]))
        self.order.save()

        self.address = Address(
            name='test address',
            address=self.wallet_address,
            currency=self.BTC,
            user=self.user,
            type=Address.DEPOSIT,
        )
        self.address.save()

        self.url_addr = 'http://btc.blockr.io/api/v1/address/txs/{}'.format(
            self.wallet_address
        )
        self.url_tx_1 = 'http://btc.blockr.io/api/v1/tx/info/{}'.format(
            self.tx_ids[0]
        )

        self.url_tx_2 = 'http://btc.blockr.io/api/v1/tx/info/{}'.format(
            self.tx_ids[1]
        )
        self.LTC = Currency.objects.get(code='LTC')
        self.ETH = Currency.objects.get(code='ETH')
        self.RNS = Currency.objects.get(code='RNS')
        self.DOGE = Currency.objects.get(code='DOGE')
        self.BCH = Currency.objects.get(code='BCH')
        self.BTC_address = self._create_withdraw_adress(
            self.BTC, '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi')
        self.LTC_address = self._create_withdraw_adress(
            self.LTC, 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA')
        self.ETH_address = self._create_withdraw_adress(
            self.ETH, '0x8116546AaC209EB58c5B531011ec42DD28EdFb71')
        self.RNS_address = self._create_withdraw_adress(
            self.RNS, 'RJrEPzpgwfhsyz2tKYxVYSAEfBNWXh8W2v')
        self.DOGE_address = self._create_withdraw_adress(
            self.DOGE, 'DPjMRpkNKEfnYVHqmAan4FbriqP4DyUt2u')
        self.BCH_address = self._create_withdraw_adress(
            self.BCH, '142banESr9veN2RkFg6k67AjDdCepdmVLm')

    def _read_fixture(self):
        path_addr_fixture = os.path.join(settings.BASE_DIR,
                                         'nexchange/tests/fixtures/'
                                         'blockr/address_transactions.json')

        path_tx1_fixture = os.path.join(settings.BASE_DIR,
                                        'nexchange/tests/fixtures/'
                                        'blockr/address_tx_1.json')

        path_tx2_fixture = os.path.join(settings.BASE_DIR,
                                        'nexchange/tests/fixtures/'
                                        'blockr/address_tx_2.json')

        uphold_get_details_fixture = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/uphold/get_card_details.json'
        )
        uphold_commit_tx_fixture = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/uphold/commit_transaction.json'
        )
        uphold_reverse_completed_fixture = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/uphold/transaction_completed.json'
        )
        uphold_reverse_pending_fixture = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/uphold/transaction_pending.json'
        )
        uphold_import_transactions_empty = os.path.join(
            settings.BASE_DIR,
            'nexchange/tests/fixtures/uphold/import_transactions_empty.json'
        )

        with open(path_addr_fixture) as f:
            self.blockr_response_addr =\
                f.read().replace('\n', '').replace(' ', '')
            self.wallet_address = json.loads(
                self.blockr_response_addr
            )['data']['address']

            txs = json.loads(self.blockr_response_addr)['data']['txs']
            self.amounts = [tx['amount'] for tx in txs]

            self.tx_ids = [tx['tx'] for tx in txs]
        with open(path_tx1_fixture) as f:
            self.blockr_response_tx1 =\
                f.read().replace('\n', '').replace(' ', '')
            self.blockr_response_tx1_parsed = json.loads(
                self.blockr_response_tx1
            )

        with open(path_tx2_fixture) as f:
            self.blockr_response_tx2 =\
                f.read().replace('\n', '').replace(' ', '')
            self.blockr_response_tx2_parsed = json.loads(
                self.blockr_response_tx2
            )

        with open(uphold_get_details_fixture) as f:
            self.uphold_get_card = \
                f.read().replace('\n', '').replace(' ', '')
            self.uphold_tx_id = json.loads(self.uphold_get_card)['id']

        with open(uphold_commit_tx_fixture) as f:
            self.uphold_commit_tx = \
                f.read().replace('\n', '').replace(' ', '')

        with open(uphold_reverse_completed_fixture) as f:
            self.uphold_tx_completed = \
                f.read().replace('\n', '').replace(' ', '')

        with open(uphold_reverse_pending_fixture) as f:
            self.uphold_tx_pending = \
                f.read().replace('\n', '').replace(' ', '')

        with open(uphold_import_transactions_empty) as f:
            self.uphold_import_transactions_empty = \
                f.read().replace('\n', '').replace(' ', '')

        self.txs = [
            self.blockr_response_tx1_parsed,
            self.blockr_response_tx2_parsed
        ]

        self.tx_texts = [
            self.blockr_response_tx1,
            self.blockr_response_tx2
        ]
        self.status_ok_list_index = 0
        self.status_bad_list_index = 1

    def _create_price_for_pair(self, pair):
        ticker = Ticker(
            pair=pair,
            ask=OrderBaseTestCase.PRICE_BUY_EUR,
            bid=OrderBaseTestCase.PRICE_SELL_EUR
        )
        ticker.save()
        price = Price(pair=pair, ticker=ticker)
        price.save()
        return price

    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    def base_test_create_transactions_with_task(self, run_method, reserve_txs,
                                                import_txs):

        pair_name = 'BTCLTC'
        pair = Pair.objects.get(name=pair_name)
        self._create_price_for_pair(pair)
        order = Order.objects.filter(pair__name=pair_name).first()
        self._create_mocks_uphold(amount2=order.amount_quote, order=order)
        reserve_txs.return_value = json.loads(self.completed)
        import_txs.return_value = json.loads(self.import_txs)
        run_method()
        tx_ok = Transaction.objects.filter(
            tx_id_api=json.loads(self.import_txs)[1]['id']
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created if order is found!'
        )
        order.refresh_from_db()
        self.assertEquals(
            order.status, Order.PAID_UNCONFIRMED,
            'Order should be marked as paid after pipeline'
        )
        tx_bad = Transaction.objects.filter(
            tx_id_api=json.loads(self.import_txs)[0]['id']
        )
        self.assertEqual(
            len(tx_bad), 0,
            'Transaction must not be created if order is not found!'
        )
        run_method()
        tx_ok = Transaction.objects.filter(
            tx_id_api=json.loads(self.import_txs)[1]['id']
        )
        self.assertEqual(
            len(tx_ok), 1,
            'Transaction must be created only one time!'
        )

    def mock_empty_transactions_for_blockchain_address(self, mock,
                                                       pattern=None):
        if pattern is None:
            pattern = '/api/v1/address/txs/{}'.format(self.address_id_pattern)
        matcher = re.compile(pattern)
        mock.get(matcher, text='{"data":{"txs":[]}}')

    def _update_withdraw_address(self, order, address):
        url = reverse('orders.update_withdraw_address',
                      kwargs={'pk': order.pk})
        self.client.post(url, {
            'pk': order.pk,
            'value': address.pk,
        })

    def _create_withdraw_adress(self, currency, address):
        addr_data = {
            'type': 'W',
            'name': address,
            'address': address,
            'currency': currency

        }
        addr = Address(**addr_data)
        addr.user = self.user
        addr.save()
        return addr

    def _create_mocks_uphold(self, amount2=Decimal('0.0'), currency1=None,
                             currency2=None, card_id=None, order=None):
        if order is not None:
            self.order = order
        if len(self.order.user.addressreserve_set.all()) == 0:
            with requests_mock.mock() as mock:
                self._mock_cards_reserve(mock)
                self._create_an_order_for_every_crypto_currency_card()
        self.tx_ids_api = ['12345', '54321']
        if not currency1:
            currency1 = self.order.pair.base.code
        if not currency2:
            currency2 = self.order.pair.quote.code
        if card_id is None and self.order.pair.quote.is_crypto:
            card_id = self.order.deposit_address.reserve.card_id
        else:
            card_id = time()
        self.import_txs = self.uphold_import_transactions_empty.format(
            tx_id_api1=self.tx_ids_api[0],
            tx_id_api2=self.tx_ids_api[1],
            amount1=self.order.amount_base,
            amount2=amount2,
            currency1=currency1,
            currency2=currency2,
            card_id=card_id,
        )
        reserve_url = 'https://api.uphold.com/v0/reserve/transactions/{}'
        self.reverse_url1 = reserve_url.format(self.tx_ids_api[0])
        self.reverse_url2 = reserve_url.format(self.tx_ids_api[1])
        self.completed = '{"status": "completed", "type": "deposit",' \
                         '"params": {"progress": 999}}'
        self.pending = '{"status": "pending", "type": "deposit"}'
