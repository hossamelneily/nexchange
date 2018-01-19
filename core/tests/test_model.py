from django.test import TestCase
from core.tests.base import OrderBaseTestCase
from core.models import AddressReserve, Currency, Pair, Transaction, Market
from core.common.models import UniqueFieldMixin
from ticker.tests.base import TickerBaseTestCase
from django.core.exceptions import ValidationError
from core.tests.utils import data_provider
from decimal import Decimal
import json
import os
from collections import Counter


class ValidateUniqueFieldMixinTestCase(TestCase):

    def test_detects_uniqe_value_colision(self):
        class UnlikelyModel(UniqueFieldMixin):
            pass

        model = UnlikelyModel()
        unq = model.gen_unique_value(
            lambda x: 'A' * x,
            lambda x: 1 if x == 'A' else 0,
            1
        )
        self.assertEqual(unq, 'UAA')


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

    def test_available_reserves(self):
        currencies = Currency.objects.all()
        for currency in currencies:
            all_r = currency.available_reserves
            self.assertTrue(isinstance(all_r, Decimal), '{}'.format(currency))
            main_r = currency.available_main_reserves
            self.assertTrue(isinstance(main_r, Decimal), '{}'.format(currency))


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


class PairFixtureTestCase(OrderBaseTestCase):

    def setUp(self):
        super(PairFixtureTestCase, self).setUp()
        self.pairs = Pair.objects.all()

    def test_pair_names(self):
        for pair in self.pairs:
            pair_name_by_code = pair.base.code + pair.quote.code
            pair_name_on_fixture = pair.name
            self.assertEqual(
                pair_name_by_code, pair_name_on_fixture,
                'pair_name on pair {} fixture .json file is bad'.format(pair)
            )

    def test_crypto_pairs_fees(self):
        major_pair_fee = Decimal('0.005')  # 0.5%
        minor_pair_fee = Decimal('0.01')  # 1.0%
        pairs = [p for p in Pair.objects.all() if p.is_crypto]
        token_pairs = [p for p in pairs if p.contains_token]
        non_token_pairs = [p for p in pairs if not p.contains_token]
        for p in non_token_pairs:
            if p.name in ['BTCLTC', 'LTCBTC', 'ETHBTC', 'BTCETH', 'BCHBTC',
                          'BTCBCH']:
                fee = major_pair_fee
            else:
                fee = minor_pair_fee
            self.assertEqual(p.fee_ask, fee, 'Bad fee_ask on {}'.format(p))
            self.assertEqual(p.fee_bid, fee, 'Bad fee_bid on {}'.format(p))
        for p in token_pairs:
            if 'ETH' in p.name:
                fee = minor_pair_fee
            elif 'BTC' in p.name:
                fee = minor_pair_fee + major_pair_fee
            else:
                fee = 2 * minor_pair_fee

            if p.quote.code == 'BDG':
                ask = Decimal('2') * fee
                bid = fee
            elif p.base.code == 'BDG':
                bid = Decimal('2') * fee
                ask = fee
            else:
                ask = bid = fee
            self.assertEqual(p.fee_ask, ask, 'Bad fee_ask on {}'.format(p))
            self.assertEqual(p.fee_bid, bid, 'Bad fee_bid on {}'.format(p))

    def test_fixture_pks(self):
        path = 'core/fixtures/'
        fixture_files = os.listdir(path)
        pair_fixtures = [name for name in fixture_files if name[:5] == 'pairs']
        currency_fixtures = [
            name for name in fixture_files if name[:8] == 'currency'
        ]
        pair_data = []
        for fix in pair_fixtures:
            pair_data += json.loads(open(path + fix).read())
        pair_pks = [record['pk'] for record in pair_data]
        pair_counter = Counter(pair_pks)
        for key, value in pair_counter.items():
            if value != 1:
                raise ValidationError(
                    'Pair pk {} repeated in fixtures!'.format(key)
                )
        currency_data = []
        for fix in currency_fixtures:
            currency_data += json.loads(open(path + fix).read())
        currency_pks = [record['pk'] for record in currency_data]
        currency_counter = Counter(currency_pks)
        for key, value in currency_counter.items():
            if value != 1:
                raise ValidationError(
                    'Currency pk {} repeated in fixtures!'.format(key)
                )


class TransactionTestCase(TickerBaseTestCase):

    def setUp(self):
        super(TransactionTestCase, self).setUp()
        self._create_order()

    def create_withdraw_txn(self, txn_type=Transaction.WITHDRAW):
        deposit_tx_id = self.generate_txn_id()
        txn_with1 = Transaction(
            amount=self.order.amount_quote,
            tx_id_api=deposit_tx_id, order=self.order,
            address_to=self.order.deposit_address,
            is_completed=True,
            is_verified=True
        )
        if txn_type is not None:
            txn_with1.type = Transaction.WITHDRAW
        txn_with1.save()
        self.order.save()

    @data_provider(lambda: (
        ('Type None', None),
    ))
    def test_do_not_save_second_withdraw_transaction(self, name, txn_type):
        self.create_withdraw_txn(txn_type=txn_type)
        with self.assertRaises(ValidationError):
            self.create_withdraw_txn(txn_type=Transaction.WITHDRAW)
        self.assertTrue(self.order.flagged, name)
        self.order.flagged = False
        self.order.save()
        with self.assertRaises(ValidationError):
            self.create_withdraw_txn(txn_type=None)
        self.assertTrue(self.order.flagged, name)


class MarketTestCase(OrderBaseTestCase):

    def test_only_one_main_market(self):
        main_market = Market.objects.get(is_main_market=True)
        other_markets = Market.objects.filter(is_main_market=False)
        for market in other_markets:
            market.is_main_market = True
            market.save()
            main_market.refresh_from_db()
            self.assertFalse(main_market.is_main_market)
            main_market = Market.objects.get(is_main_market=True)
            self.assertEqual(market, main_market)

    def test_market_str(self):
        markets = Market.objects.all()
        for market in markets:
            str = market.__str__
            self.assertTrue(str)
