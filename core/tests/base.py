from decimal import Decimal
import json
import datetime

from core.tests.utils import set_big_reserves
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import Client, TestCase
from django.utils.translation import activate

from accounts.models import SmsToken
from core.models import Currency, Address, Transaction, Pair, AddressReserve
from core.tests.utils import get_ok_pay_mock, split_ok_pay_mock
from orders.models import Order
from payments.models import PaymentPreference
from payments.utils import get_sha256_sign
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
from web3 import Web3
from nexchange.rpc.ethash import EthashRpcApiClient
from django.test import RequestFactory
from axes.models import AccessAttempt
from django.core.servers.basehttp import WSGIServer
from django.test.testcases import LiveServerTestCase, LiveServerThread,\
    QuietWSGIRequestHandler
from django.contrib.staticfiles.handlers import StaticFilesHandler
from payments.views import SafeChargeListenView
from nexchange.rpc.scrypt import ScryptRpcApiClient
from rest_framework.test import APIClient
import warnings
from django.contrib.auth import authenticate


UPHOLD_ROOT = 'nexchange.api_clients.uphold.Uphold.'
SCRYPT_ROOT = 'nexchange.rpc.scrypt.ScryptRpcApiClient.'
ZCASH_ROOT = 'nexchange.rpc.zcash.ZcashRpcApiClient.'
OMNI_ROOT = 'nexchange.rpc.omni.OmniRpcApiClient.'
ETH_ROOT = 'nexchange.rpc.ethash.EthashRpcApiClient.'
BLAKE2_ROOT = 'nexchange.rpc.blake2.Blake2RpcApiClient.'
CRYPTONIGHT_ROOT = 'nexchange.rpc.cryptonight.CryptonightRpcApiClient.'
RIPPLE_ROOT = 'nexchange.rpc.ripple.RippleRpcApiClient.'
BITTREX_ROOT = 'nexchange.api_clients.bittrex.BittrexApiClient.'

EXCHANGE_ORDER_RELEASE_ROOT = 'orders.tasks.generic.exchange_order_release.' \
                              'ExchangeOrderRelease.'

RPC8_PASSWORD = 'password'
RPC8_HOST = '0.0.0.0'
RPC8_PORT = '0000'
RPC8_USER = 'user'
RPC8_WALLET = '1234'
RPC8_PUBLIC_KEY_C1 = 'xrb_1maincard'
RPC8_URL = 'http://{}:{}@{}/'.format(RPC8_USER, RPC8_PASSWORD, RPC8_HOST)
RPC13_URL = RPC11_URL = 'http://{}/json_rpc'.format(RPC8_HOST)


class NexchangeLiveServerThread(LiveServerThread):
    def _create_server(self):
        return WSGIServer((self.host, self.port), QuietWSGIRequestHandler,
                          allow_reuse_address=False)


class NexchangeLiveServerTestCase(LiveServerTestCase):
    server_thread_class = NexchangeLiveServerThread


class NexchangeStaticLiveServerTestCase(NexchangeLiveServerTestCase):
    static_handler = StaticFilesHandler


class NexchangeClient(Client):
    def login(self, **credentials):
        request = RequestFactory().get('/')
        request.user = credentials
        user = authenticate(request, **credentials)
        if user:
            self._login(user)
            return True
        else:
            return False


class UserBaseTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(UserBaseTestCase, self).__init__(*args, **kwargs)
        self.rpc_mock = None
        self.api_client = APIClient()

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
        set_big_reserves()
        self.patcher_validate_order_reserve = patch(
            'orders.models.Order._validate_reserves'
        )
        self.patcher_validate_order_reserve.start()
        self.patcher_validate_order_create_price = patch(
            'orders.models.Order._validate_price'
        )
        self.patcher_validate_order_create_price.start()
        self.patcher_validate_ticker_diff = patch(
            'ticker.models.Ticker._validate_change'
        )
        self.patcher_validate_ticker_diff.start()
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
        self.create_main_user()

        assert isinstance(self.user, User)
        token = SmsToken(user=self.user)
        token.save()
        self.client = NexchangeClient()
        success = self.client.login(username=self.username,
                                    password=self.password)
        assert success
        super(UserBaseTestCase, self).setUp()

    def tearDown(self):
        super(UserBaseTestCase, self).tearDown()
        for patcher in [self.patcher_validate_order_reserve,
                        self.patcher_validate_order_create_price,
                        self.patcher_validate_ticker_diff]:
            try:
                patcher.stop()
            except RuntimeError:
                continue
        AccessAttempt.objects.all().delete()

    @patch('orders.models.Order.calculate_quote_from_base')
    def create_main_user(self, convert_cash):
        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            self.user, created = \
                User.objects.get_or_create(username=self.username)
            self.user.set_password(self.password)
            self.user.save()

    def _get_id(self, prefix, pattern=None):
        id = str(time()).split('.')[1]
        # 4 digits hex - [0x1000:0x10000), sensitive for ETH address pattern
        rand = randint(4096, 65535)
        if pattern is None:
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

    # deprecated
    def _mock_cards_reserve(self, _mock):
        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_create',
                    params.get('wallet')]):
                return {'account': self._get_id('xrb_')}
            if params.get('method') == 'create_address':
                return {'id': 0,
                        'jsonrpc': '2.0',
                        'result': {
                            'address': self._get_id('4'),
                            'address_index': 6}
                        }
            if params.get('method') == 'open_wallet':
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}
            if params.get('method') == 'stop_wallet':
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}

        _mock.post(RPC8_URL, json=text_callback)
        _mock.post(RPC11_URL, json=text_callback)
        pattern_addr = re.compile('https://api.uphold.com/v0/me/cards/.+/addresses')  # noqa
        _mock.post(pattern_addr, text=self._request_address)

    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC8_WALLET': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC8_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    @patch.dict(os.environ, {'RPC11_PUBLIC_KEY_C1': RPC8_PUBLIC_KEY_C1})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_NAME': RPC8_WALLET})
    @patch.dict(os.environ, {'RPC_RPC11_WALLET_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC_RPC11_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC11_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC11_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC11_PORT': RPC8_PORT})
    @patch.dict(os.environ, {'RPC13_PUBLIC_KEY_C1': 'ry34sxfxsdfsdfsdf2342r'})
    @patch.dict(os.environ, {'RPC_RPC13_PASSWORD': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_K': RPC8_PASSWORD})
    @patch.dict(os.environ, {'RPC_RPC13_USER': RPC8_USER})
    @patch.dict(os.environ, {'RPC_RPC13_HOST': RPC8_HOST})
    @patch.dict(os.environ, {'RPC_RPC13_PORT': RPC8_PORT})
    @requests_mock.mock()
    def _create_order(self, mock, order_type=Order.BUY,
                      amount_base=0.5, pair_name='LTCBTC',
                      payment_preference=None, user=None, amount_quote=None,
                      validate_amount=False, payment_id=None, dest_tag=None):
        warnings.warn(
            'UserBaseTestCase._create_order should be changed with '
            'OrderBaseTestCase._create_order_api or any other method which '
            'uses API to create orders ',
            DeprecationWarning
        )

        def text_callback(request, context):
            body = request._request.body
            params = json.loads(body)
            if all([params.get('action') == 'account_create',
                    params.get('wallet')]):
                return {'account': self._get_id('xrb_')}
            if params.get('method') == 'create_address':
                return {'id': 0,
                        'jsonrpc': '2.0',
                        'result': {
                            'address': self._get_id('4'),
                            'address_index': 6}
                        }
            if params.get('method') == 'open_wallet':
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}
            if params.get('method') == 'store':
                return {'id': 0, 'jsonrpc': '2.0', 'result': {}}
        mock.post(RPC8_URL, json=text_callback)
        mock.post(RPC11_URL, json=text_callback)

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
        if dest_tag is not None:
            self.order.destination_tag = dest_tag
        if payment_preference is not None:
            self.order.payment_preference = payment_preference
        if validate_amount:
            self.order.save()
            return
        with patch('orders.models.Order._validate_order_amount') as p:
            p.return_value = None
            self.order.save()

    @patch('core.models.Currency.is_quote_of_enabled_pair')
    def _create_an_order_for_every_crypto_currency_card(self, user, is_quote,
                                                        amount_quote=None):
        is_quote.return_value = True
        crypto_currencies = Currency.objects.filter(is_crypto=True).exclude(
            code='RNS')
        for curr in crypto_currencies:
            pair = Pair.objects.filter(quote__code=curr)
            if not pair:
                continue
            pair_name = pair.first().name
            self._create_order(user=user, pair_name=pair_name,
                               amount_quote=amount_quote)


class OrderBaseTestCase(UserBaseTestCase):
    fixtures = [
        'market.json',
        'currency_algorithm.json',
        'transaction_price.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'currency_tokens.json',
        'country.json',
        'pairs_cross.json',
        'pairs_btc.json',
        'pairs_eth.json',
        'pairs_ltc.json',
        'pairs_rns.json',
        'pairs_doge.json',
        'pairs_bch.json',
        'pairs_xvg.json',
        'pairs_nano.json',
        'pairs_omg.json',
        'pairs_bdg.json',
        'pairs_eos.json',
        'pairs_zec.json',
        'pairs_usdt.json',
        'pairs_xmr.json',
        'pairs_kcs.json',
        'pairs_bnb.json',
        'pairs_knc.json',
        'pairs_bix.json',
        'pairs_ht.json',
        'pairs_bnt.json',
        'pairs_coss.json',
        'pairs_cob.json',
        'pairs_dash.json',
        'pairs_bmh.json',
        'pairs_xrp.json',
        'payment_method.json',
        'payment_preference.json',
        'reserve.json',
        'account.json',
        'tier0.json',
        'tier1.json',
        'tier2.json',
        'tier3.json',
        'document_type.json',
        'fee_source.json'
    ]
    PRICE_BUY_RUB = 36000
    PRICE_BUY_USD = 600
    PRICE_BUY_EUR = 500

    PRICE_SELL_RUB = 30000
    PRICE_SELL_USD = 500
    PRICE_SELL_EUR = 400

    RATE_EUR = 70.00

    TEST_ADDRESSES = {
        'BTC': '17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ',
        'LTC': 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA',
        'ETH': '0x8116546AaC209EB58c5B531011ec42DD28EdFb71',
        'XVG': 'DQkwDpRYUyNNnoEZDf5Cb3QVazh4FuPRs9',
    }

    def setUp(self):

        super(OrderBaseTestCase, self).setUp()
        self._mock_rpc()
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
        self.ethash_client = EthashRpcApiClient()
        self.default_eth_from = '0x1ff21eca1c3ba96ed53783ab9c92ffbf77862584'

    def _mock_rpc(self):
        def addr_response(_self, currency):
            pattern = None
            if currency.wallet == 'rpc7':
                pattern = '0x{rand:02x}' + ('1' * 36)
            return {
                'address': self._get_id('addr', pattern=pattern),
                'currency': currency
            }

        def ethash_addr_response(_self, currency):
            pattern = '0x{rand:02x}' + ('1' * 36)
            return self._get_id('addr', pattern=pattern)

        self.rpc_mock_addr = \
            mock.patch(SCRYPT_ROOT + 'create_address',
                       new=addr_response)
        self.rpc_mock_addr.start()
        self.rpc_mock_backup = \
            mock.patch(SCRYPT_ROOT + 'backup_wallet',
                       new=addr_response)
        self.rpc_mock_backup.start()
        self.zcash_mock_backup = \
            mock.patch(ZCASH_ROOT + 'backup_wallet',
                       new=addr_response)
        self.zcash_mock_backup.start()
        self.omni_mock_backup = \
            mock.patch(OMNI_ROOT + 'backup_wallet',
                       new=addr_response)
        self.omni_mock_backup.start()

        self.rpc_eth_mock_addr = \
            mock.patch('web3.personal.Personal.newAccount',
                       new=ethash_addr_response)
        self.rpc_eth_mock_addr.start()
        self.rpc_eth_mock_passw = \
            mock.patch('nexchange.rpc.ethash.RpcMapper.get_pass',
                       return_value='very_password')
        self.rpc_eth_mock_passw.start()

        self.mock_rpc_txs = mock.patch(SCRYPT_ROOT + '_get_txs',
                                       lambda _self, *args: [])
        self.mock_rpc_txs.start()

    def _stop_rpc_mock(self):
        self.rpc_mock_addr.stop()
        self.rpc_mock_backup.stop()
        self.mock_rpc_txs.stop()
        self.rpc_eth_mock_addr.stop()
        self.rpc_eth_mock_passw.stop()
        self.zcash_mock_backup.stop()
        self.omni_mock_backup.stop()

    def tearDown(self):
        super(OrderBaseTestCase, self).tearDown()
        self.patcher_twilio_send_sms.stop()
        self.patcher_twilio_send_sms2.stop()
        self.patcher_send_email.stop()
        self.patcher_send_email2.stop()
        self.patcher_uphold_reserve_txn.stop()
        # self.card.delete()

        # rpc
        self._stop_rpc_mock()

    @classmethod
    def setUpClass(cls):
        super(OrderBaseTestCase, cls).setUpClass()

        cls.patcher_validate_ticker_diff = patch(
            'ticker.models.Ticker._validate_change'
        )
        cls.patcher_validate_ticker_diff.start()

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
        cls.patcher_validate_ticker_diff.stop()

    @patch(SCRYPT_ROOT + '_list_txs')
    def move_order_status_up(self, order, _from, _to, list_txs):
        list_txs.return_value = []
        api = ScryptRpcApiClient()
        sc = SafeChargeListenView()
        while order.status != _to:
            _before = order.status
            _crypto = order.pair.is_crypto
            if order.status == Order.INITIAL:
                tx_data = {
                    'order': order,
                    'currency': order.pair.quote,
                    'type': Transaction.DEPOSIT,
                }
                if not _crypto:
                    pref = sc.get_or_create_payment_preference(
                        self.generate_txn_id(),
                        'Test McFerrin',
                        order.unique_reference,
                        order.payment_preference.payment_method,
                    )
                    tx_data.update({
                        'amount_cash': order.amount_quote,
                        'user': order.user,
                        'payment_preference': pref,
                        'payment_system_id': self.generate_txn_id(),
                        'secondary_payment_system_id': self.generate_txn_id(),
                        'auth_code': self.generate_txn_id(),
                        'reference': order.unique_reference,

                    })
                else:
                    tx_data.update({
                        'amount': order.amount_quote,
                        'address_to': order.deposit_address
                    })
                order.register_deposit(tx_data, crypto=order.pair.is_crypto)
            elif order.status == Order.PAID_UNCONFIRMED:
                tx = order.transactions.get() if _crypto else order.\
                    payment_set.get()
                order.confirm_deposit(tx, crypto=_crypto)
            elif order.status == Order.PAID:
                with patch(SCRYPT_ROOT + 'health_check') as _health:
                    _health.return_value = True
                    order.pre_release(api=api)
            elif order.status == Order.PRE_RELEASE:
                tx_data = {
                    'order': order,
                    'address_to': order.withdraw_address,
                    'amount': order.amount_base,
                    'currency': order.pair.base,
                    'type': Transaction.WITHDRAW
                }
                with patch(SCRYPT_ROOT + 'release_coins') as _release:
                    _release.return_value = self.generate_txn_id(), True
                    order.release(tx_data, api=api)
            elif order.status == Order.RELEASED:
                tx = order.transactions.get(type='W') if _crypto else order. \
                    payment_set.get()
                order.complete(tx)
            self.assertEqual(_before + 1, order.status)

    def _get_default_address(self, pair=None):
        # add currency logic if needed
        if pair:
            _pair = pair if isinstance(pair, Pair) \
                else Pair.objects.get(name=pair)
            _currency = _pair.base
        else:
            _currency = Currency.objects.get('BTC')

        return self.TEST_ADDRESSES.get(_currency.code)

    def _create_order_api(self, **kwargs):
        order_data = kwargs.get('order_data', None)
        pair_name = kwargs.get('pair_name', 'BTCEUR')
        withdraw_address = kwargs.get(
            'withdraw_address', self._get_default_address(pair=pair_name)
        )
        amount_base = kwargs.get('amount_base', None)
        amount_quote = kwargs.get('amount_quote', 100)
        if not order_data:
            order_data = {
                "pair": {
                    "name": pair_name
                },
                "withdraw_address": {
                    "address": withdraw_address
                }
            }
            if amount_base:
                order_data.update({'amount_base': amount_base})
            if amount_quote:
                order_data.update({'amount_quote': amount_quote})
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
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

    def get_ripple_sign_response(self, card_address, value,
                                 withdraw_address, dest_tag, tx_id):
        return {'result': {
            'status': 'success',
            'tx_blob': 'blob_hash322',
            'tx_json': {
                'Account': card_address,
                'Amount': value,
                'Destination': withdraw_address,
                'DestinationTag': dest_tag,
                'Sequence': 22,
                'TransactionType': 'Payment',
                'hash': tx_id
            }}}

    def get_ripple_raw_tx(self, raw_amount, address_to, dest_tag, tx_id):
        _txs = self.get_ripple_raw_txs(
            raw_amount, address_to, dest_tag, tx_id
        ).get('result')
        tx = _txs.get('transactions')[0].get('tx')
        tx['meta'] = _txs.get('transactions')[0].get('meta')
        tx['status'] = "success"
        tx['validated'] = True
        return tx

    def get_ripple_raw_txs(self, raw_amount, address_to, dest_tag, tx_id):
        return {'result': {
            'status': 'success',
            'transactions': [{
                "meta": {
                    "TransactionIndex": 1,
                    "TransactionResult": "tesSUCCESS",
                    "delivered_amount": raw_amount
                },
                'tx': {
                    'Account': 'r9y61YwVUQtTWHtwcmYc1Epa5KvstfUzSm',
                    'Amount': raw_amount,
                    'Destination': address_to,
                    "DestinationTag": dest_tag,
                    'Fee': '10',
                    'Sequence': 6,
                    'TransactionType': 'Payment',
                    'hash': tx_id,
                    'inLedger': 10326866,
                    'ledger_index': 10326866
                },
                'validated': True
            }]
        }}

    def get_omni_raw_txs(self, value, address):
        return [{
            'txid': self.generate_txn_id(),
            'fee': '0.00002896',
            'sendingaddress': '17vzvhu6QMUTVYxz7M5TBmXPYbVQQ9mGcZ',
            'referenceaddress': address,
            'ismine': True,
            'type_int': 0,
            'type': 'Simple Send',
            'propertyid': 31,
            'amount': value,
            'valid': True,
            'confirmations': 1
        }]

    def get_omni_tx_raw_confirmed(self, value, address):
        tx = self.get_omni_raw_txs(value, address)[0]
        tx['confirmations'] = 7
        tx['valid'] = True
        return tx

    def get_omni_tx_raw_unconfirmed(self, value, address):
        tx = self.get_omni_raw_txs(value, address)[0]
        tx['confirmations'] = 1
        tx['valid'] = False
        return tx

    def get_cryptonight_raw_txs(self, currency, amount, address, block_height,
                                payment_id):
        raw_amount = str(int(amount * (10 ** currency.decimals)))
        return {
            'id': 0,
            'jsonrpc': '2.0',
            'result': {
                'in': [{
                    'address': address,
                    'amount': raw_amount,
                    'double_spend_seen': False,
                    'fee': 950700000,
                    'height': block_height,
                    'note': '',
                    'payment_id': payment_id,
                    'subaddr_index': {'major': 0, 'minor': 0},
                    'timestamp': 1525336581,
                    'txid': self.generate_txn_id(),
                    'type': 'in',
                    'unlock_time': 0
                }]
            }
        }

    def get_cryptonight_raw_tx(self, raw_txs):
        tx_data = raw_txs['result']['in'][0]
        return {
            'id': 0,
            'jsonrpc': '2.0',
            'result': {
                'transfer': tx_data
            }
        }

    def get_ethash_tx(self, amount, address):
        value = Web3.toWei(amount, 'ether')
        return [{
            'data': {},
            'to': address,
            'value': value,
            'tx_id': self.generate_txn_id(),
            'currency_code': 'ETH',
        }]

    def get_ethash_tx_raw(self, currency, amount, address, block_number=1,
                          _from=None):
        if _from is None:
            _from = self.default_eth_from
        if currency.is_token:
            main_value = 0
            main_to = currency.contract_address
            value = int(
                Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
            )
            input = self.ethash_client.get_data_hash(
                'transfer(address,uint256)', *[address, hex(value)]
            )
        else:
            main_value = Web3.toWei(amount, 'ether')
            main_to = address
            input = '0x'
        return {
            'hash': self.generate_txn_id(),
            'input': input,
            'nonce': 0,
            'to': main_to,
            'from': _from,
            'value': main_value,
            'blockNumber': block_number
        }

    def get_ethash_tx_receipt_raw(self, currency, amount, status=1, _to='0x',
                                  _from=None, successful_logs=True):

        value = int(
            Decimal(amount) * Decimal('1e{}'.format(currency.decimals))
        )
        if _from is None:
            _from = self.default_eth_from
        if currency.is_token:
            return {
                'status': status,
                'logs': [{
                    'data': hex(value) if successful_logs else '0x',
                    'topics': [_from, _to] if successful_logs else []
                }]
            }
        else:
            return {'status': status}

    def get_ethash_block_raw(self, currency, amount, address):
        return {
            'transactions': [
                self.get_ethash_tx_raw(currency, amount, address)
            ]
        }

    def get_blake2_raw_tx(self, currency, amount, address):
        raw_amount = str(int(amount * (10 ** currency.decimals)))
        return {
            'history': [{
                'type': 'receive',
                'hash': self.generate_txn_id(),
                'amount': raw_amount
            }]
        }

    def get_blake2_raw_tx_send(self, currency, amount, address):
        raw_amount = str(int(amount * (10 ** currency.decimals)))
        return {
            'history': [{
                'type': 'send',
                'account': address,
                'hash': self.generate_txn_id(),
                'amount': raw_amount
            }]
        }

    def get_cryptonight_tx(self, raw_tx):
        return raw_tx['result']['in']

    def get_scrypt_tx(self, amount, address):
        return [{
            'address': address,
            'category': 'receive',
            'account': '',
            'amount': amount,
            'txid': self.generate_txn_id(),
            'confirmations': 0,
            'timereceived': 1498736269,
            'time': 1498736269,
            'fee': Decimal('-0.00000100')
        }]

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
            'amount_base': Decimal(0.1),
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
        'currency_algorithm.json',
        'transaction_price.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'currency_tokens.json',
        'pairs_cross.json',
        'pairs_btc.json',
        'pairs_ltc.json',
        'pairs_rns.json',
        'pairs_eth.json',
        'pairs_doge.json',
        'pairs_bch.json',
        'pairs_xvg.json',
        'pairs_nano.json',
        'pairs_omg.json',
        'pairs_bdg.json',
        'pairs_eos.json',
        'pairs_zec.json',
        'pairs_usdt.json',
        'pairs_xmr.json',
        'pairs_kcs.json',
        'pairs_bnb.json',
        'pairs_knc.json',
        'pairs_bix.json',
        'pairs_ht.json',
        'pairs_bnt.json',
        'pairs_coss.json',
        'pairs_cob.json',
        'pairs_dash.json',
        'pairs_bmh.json',
        'pairs_xrp.json',
        'payment_method.json',
        'payment_preference.json',
        'reserve.json',
        'account.json',
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
            amount_base=0.2,
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
        xmr_card = AddressReserve(
            currency=Currency.objects.get(code='XMR'),
            address='41pLNkSGSJK8pWAG9dd57YcWB82gH5ucHNEPnGt1FBN59P'
                    'rdYqKUGB1SfZxGQPcYcDEbctmpN2kpVbtuie6yCRf16oXkjuY',
        )
        xmr_card.save()
        xrp_card = AddressReserve(
            currency=Currency.objects.get(code='XRP'),
            address='rnErCcvuHdxfUEcU81NtujYv36mQ4BaSP2'
        )
        xrp_card.save()

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
        self.ZEC = Currency.objects.get(code='ZEC')
        self.USDT = Currency.objects.get(code='USDT')
        self.XMR = Currency.objects.get(code='XMR')
        self.DASH = Currency.objects.get(code='DASH')
        self.XRP = Currency.objects.get(code='XRP')
        self.XVG = Currency.objects.get(code='XVG')
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
        self.ZEC_address = self._create_withdraw_adress(
            self.ZEC, 't1a7HFeidzBswwdXaFV1gKtSphn41rLcEmK'
        )
        self.USDT_address = self._create_withdraw_adress(
            self.USDT, '1AzrxFRwxGmXPeSum9Bsisv7XxhSAeANwH'
        )
        self.XMR_address = self._create_withdraw_adress(
            self.XMR, '41pLNkSGSJK8pWAG9dd57YcWB82gH5ucHNEPnGt1FBN59P'
                      'rdYqKUGB1SfZxGQPcYcDEbctmpN2kpVbtupm6yCRf16oXkjuY')
        self.DASH_address = self._create_withdraw_adress(
            self.DASH, 'XgJdGA5NWn71TmFYxVPvpZxUKAe8x7YWrP'
        )
        self.XRP_address = self._create_withdraw_adress(
            self.XRP, 'r9y61YwVUQtTWHtwcmYc1Epa5KvstfUzSm'
        )
        self.XVG_address = self._create_withdraw_adress(
            self.XVG, 'DQkwDpRYUyNNnoEZDf5Cb3QVazh4FuPRs9'
        )

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

    def _update_withdraw_address(self, order, address):
        order.refresh_from_db()
        order.withdraw_address = address
        order.save()

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
        order = self.order if not order else order
        if len(self.order.user.addressreserve_set.all()) == 0:
            with requests_mock.mock() as mock:
                self._mock_cards_reserve(mock)
                self._create_an_order_for_every_crypto_currency_card(self.user)
        if order is not None:
            self.order = order
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


class VerificationBaseTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(VerificationBaseTestCase, self).__init__(*args, **kwargs)
        self.rpc_mock = None

    @classmethod
    def setUpClass(cls):
        super(VerificationBaseTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(VerificationBaseTestCase, cls).tearDownClass()

    def setUp(self):
        super(VerificationBaseTestCase, self).setUp()

        self.bankbins_resp = {
            'bin': '000000',
            'bank': 'Bank of Samael',
            'card': 'VISA',
            'type': 'FAVOR',
            'level': 'DEVIL',
            'countrycode': 'US',
            'website': 'https://not.a.good.idea',
            'phone': '(961-1) 738938 - 743300 '
                     'OR (961-1) 372780 - 370830 - 373102',
            'valid': 'true'
        }

    def tearDown(self):
        super(VerificationBaseTestCase, self).tearDown()

    def _create_kyc(self, ref):
        id_doc = self._create_image()
        util_doc = self._create_image()
        selfie = self._create_image()
        whitelist_selfie = self._create_image()
        order_data = {
            "order_reference": ref,
            "identity_document": id_doc,
            "utility_document": util_doc,
            "selfie": selfie,
            "whitelist_selfie": whitelist_selfie
        }
        order_api_url = '/en/api/v1/kyc/'
        self.api_client.post(
            order_api_url, order_data, format='multipart'
        )
        id_doc.close()
        util_doc.close()
        selfie.close()
        kyc = Verification.objects.latest('id')
        user = kyc.user
        user.email = 'example@eeee.com'
        user.save()
        return kyc

    def _create_image(self):
        from PIL import Image
        from io import BytesIO
        from django.core.files.base import ContentFile

        # create Mockup picture
        image = Image.new('RGBA', size=(50, 50), color=(155, 0, 0))
        image_file = BytesIO(image.tobytes())
        image_file.name = 'test.png'
        image_file.seek(0)
        return ContentFile(image_file.read(), 'test.png')

    def _create_order_api(self, set_pref=False, order_data=None,
                          pair_name='BTCEUR',
                          address='17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ'):
        if not order_data:
            order_data = {
                "amount_quote": 100,
                "pair": {
                    "name": pair_name
                },
                "withdraw_address": {
                    "address": address
                }
            }
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        if set_pref:
            order.payment_preference = self.pref
            order.save()
        return order

    def generate_txn_id(self):
        txn_id = 'txid_{}{}'.format(time(), randint(1, 999))
        return txn_id

    def _get_dmn_request_params_for_order(self, order, unique_cc, name,
                                          status='APPROVED', time_stamp=None,
                                          payment_method='cc_card'):
        order.refresh_from_db()
        time_stamp = time_stamp if time_stamp else \
            datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
        key = settings.SAFE_CHARGE_SECRET_KEY
        total_amount = str(order.amount_quote)
        currency = order.pair.quote.code
        ppp_tx_id = self.generate_txn_id()
        product_id = order.unique_reference
        to_hash = (key, total_amount, currency, time_stamp, ppp_tx_id, status,
                   product_id)
        checksum = get_sha256_sign(ar_hash=to_hash, delimiter='',
                                   upper=False)
        params = {
            'PPP_TransactionID': ppp_tx_id,
            'productId': product_id,
            'totalAmount': total_amount,
            'currency': currency,
            'advancedResponseChecksum': checksum,
            'Status': status,
            'responseTimeStamp': time_stamp,
            'uniqueCC': unique_cc,
            'nameOnCard': name,
            'payment_method': payment_method,
            'bin': self.bankbins_resp['bin']
        }
        return params
