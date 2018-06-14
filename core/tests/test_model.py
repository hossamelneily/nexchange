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
from risk_management.models import Account
from unittest.mock import patch
from django.db.models import Max


class ValidateUniqueFieldMixinTestCase(TestCase):

    def test_detects_unique_value_colision(self):
        class UnlikelyModel(UniqueFieldMixin):
            pass

        model = UnlikelyModel()
        unique_ref = model.gen_unique_value(
            lambda x: 'A' * x,
            lambda x: 1 if x == 'UA' else 0,
            1
        )
        self.assertEqual(unique_ref, 'UAA')

    @patch('core.common.models.UniqueFieldMixin.get_random_unique_reference')
    def test_unique_reference_is_upper(self, mock_get_random_ur):

        class UnlikelyModel(UniqueFieldMixin):
            pass

        model = UnlikelyModel()
        string_array = ['Aa111', 'bdAcs', 'gggg2']
        prefix = model.__class__.__name__[:1]
        for string in string_array:
            mock_get_random_ur.return_value = string
            unique_ref = model.gen_unique_value(
                lambda x: model.get_random_unique_reference(5),
                lambda x: 0,
                5
            )
            self.assertEqual(unique_ref, prefix + string.upper())


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

    def test_currency_has_account_and_reserves(self):
        path_accounts = 'risk_management/fixtures/account.json'
        path_reserve = 'risk_management/fixtures/reserve.json'
        path_currencies = ['core/fixtures/currency_crypto.json',
                           'core/fixtures/currency_tokens.json']
        currencies_data = []
        for path in path_currencies:
            currencies_data += json.loads(open(path).read())
        accounts_data = json.loads(open(path_accounts).read())
        reserve_data = json.loads(open(path_reserve).read())
        currencies_pk = [currency['pk'] for currency in currencies_data
                         if currency['pk'] not in [33, 41,
                                                   38]]  # ignore RNS, GNT, OMG
        currencies_pk_in_reserve = [reserve['fields']['currency']
                                    for reserve in reserve_data]
        reserves_pk = [reserve['pk'] for reserve in reserve_data]
        reserves_pk_in_accounts = [account['fields']['reserve'] for account
                                   in accounts_data]
        is_currency_in_reserves = \
            set(currencies_pk).issubset(set(currencies_pk_in_reserve))
        self.assertTrue(is_currency_in_reserves,
                        'Missing reserve for currency %s' %
                        (set(currencies_pk) - set(currencies_pk_in_reserve)))
        is_reserve_in_accounts = \
            set(reserves_pk).issubset(set(reserves_pk_in_accounts))
        self.assertTrue(is_reserve_in_accounts,
                        'Missing account for reserve %s' %
                        (set(reserves_pk) - set(reserves_pk_in_accounts)))

    def test_move_currency_to_test_mode_if_account_below_requirements(self):
        curr = Currency.objects.get(code='BTC')
        account = Account.objects.get(reserve__currency=curr,
                                      is_main_account=True)
        # Set minimu level as 0
        account.reserve.minimum_level = Decimal('0')
        account.reserve.save()
        self.assertFalse(curr.execute_cover)
        self.assertTrue(curr.is_base_of_enabled_pair)
        self.assertTrue(curr.is_base_of_enabled_pair_for_test)
        # Set reserves level to less than minimal
        account.available = \
            account.reserve.minimum_main_account_level * Decimal('0.99')
        account.save()
        curr.refresh_from_db()
        self.assertFalse(curr.has_enough_reserves)
        self.assertFalse(curr.is_base_of_enabled_pair)
        self.assertTrue(curr.is_base_of_enabled_pair_for_test)
        # Executable pairs can have less reserves
        curr.execute_cover = True
        curr.save()
        self.assertTrue(curr.has_enough_reserves)
        self.assertTrue(curr.is_base_of_enabled_pair)
        self.assertTrue(curr.is_base_of_enabled_pair_for_test)


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
        # NOTE: avoid super() here, save() edits fixtures (i.e. save is called
        # on enable_all_pairs)
        self.pairs = Pair.objects.all()
        self.path = 'core/fixtures/'

    def tearDown(self):
        pass

    def test_pair_names(self):
        for pair in self.pairs:
            pair_name_by_code = pair.base.code + pair.quote.code
            pair_name_on_fixture = pair.name
            self.assertEqual(
                pair_name_by_code, pair_name_on_fixture,
                'pair_name on pair {} fixture .json file is bad. Base: {} '
                'quote {} pk {}'.format(pair, pair.base, pair.quote, pair.pk)
            )

    def test_crypto_pairs_fees(self):
        major_pair_fee = Decimal('0.005')  # 0.5%
        minor_pair_fee = Decimal('0.01')  # 1.0%
        pairs = [
            p for p in Pair.objects.exclude(
                base__code='RNS'
            ).exclude(
                quote__code='RNS'
            ) if p.is_crypto or p.quote.code in ['USD', 'EUR', 'GBP', 'JPY']]
        token_pairs = [p for p in pairs if p.contains_token]
        non_token_pairs = [p for p in pairs if not p.contains_token]
        for p in non_token_pairs:
            if p.name in ['BTCLTC', 'LTCBTC', 'ETHBTC', 'BTCETH', 'BCHBTC',
                          'BTCBCH', 'BTCEUR']:
                fee = major_pair_fee
            else:
                fee = minor_pair_fee
            if p.quote.code in ['USD', 'JPY']:
                fee += Decimal('0.02')
            if 'GBP' == p.quote.code:
                fee += Decimal('0.01')
            self.assertEqual(p.fee_ask, fee, 'Bad fee_ask on {}'.format(p))
            self.assertEqual(p.fee_bid, fee, 'Bad fee_bid on {}'.format(p))
        for p in token_pairs:
            # if 'ETH' in p.name:
            #     fee = minor_pair_fee
            # elif 'BTC' in p.name:
            #     fee = minor_pair_fee + major_pair_fee
            # else:
            #     fee = 2 * minor_pair_fee
            #  ICO fees
            fee = minor_pair_fee

            # if p.quote.code in ['BDG', 'BIX', 'HT', 'COSS', 'COB']:
            #     ask = Decimal('2') * fee
            #     bid = fee
            # elif p.base.code in ['BDG', 'BIX', 'HT', 'COSS', 'COB']:
            #     bid = Decimal('2') * fee
            #     ask = fee
            # else:
            #     ask = bid = fee
            #  ICO fees
            ask = bid = fee
            if p.quote.code in ['USD', 'JPY']:
                ask += Decimal('0.02')
                bid += Decimal('0.02')
            elif 'GBP' == p.quote.code:
                ask += Decimal('0.01')
                bid += Decimal('0.01')
            self.assertEqual(p.fee_ask, ask, 'Bad fee_ask on {}'.format(p))
            self.assertEqual(p.fee_bid, bid, 'Bad fee_bid on {}'.format(p))

    def test_fixture_pks(self):
        fixture_files = os.listdir(self.path)
        pair_fixtures = [name for name in fixture_files if name[:5] == 'pairs']
        currency_fixtures = [
            name for name in fixture_files if name[:8] == 'currency'
        ]
        pair_data = []
        for fix in pair_fixtures:
            pair_data += json.loads(open(self.path + fix).read())
        pair_pks = [record['pk'] for record in pair_data]
        pair_counter = Counter(pair_pks)
        for key, value in pair_counter.items():
            if value != 1:
                raise ValidationError(
                    'Pair pk {} repeated in fixtures!'.format(key)
                )
        currency_data = []
        for fix in currency_fixtures:
            currency_data += json.loads(open(self.path + fix).read())
        currency_pks = [record['pk'] for record in currency_data]
        currency_counter = Counter(currency_pks)
        for key, value in currency_counter.items():
            if value != 1:
                raise ValidationError(
                    'Currency pk {} repeated in fixtures!'.format(key)
                )

    def test_crypto_crypto_pairs_fulfillment(self):
        currency_fixtures = ['currency_crypto.json', 'currency_tokens.json']
        pair_fixture = 'pairs_cross.json'
        pairs_data = json.loads(open(self.path + pair_fixture).read())
        currency_data = []
        for fix in currency_fixtures:
            currency_data += json.loads(open(self.path + fix).read())
        cryptos = [data for data in currency_data
                   if data['fields']['code'] not in ['RNS', 'GNT', 'QTM']]
        for crypto in cryptos:
            expected_pairs_amount = len(cryptos) - 1
            pairs = [pair for pair in pairs_data
                     if pair['fields']['base'] == crypto['pk'] and
                     pair['fields']['quote']
                     not in [33, 41, 38]]  # ignore RNS, GNT, QTM pks
            fit_pairs = []
            for pair in pairs:
                fit_pairs.append(pair['fields']['name'])
            self.assertEquals(expected_pairs_amount,
                              len(fit_pairs),
                              '%s has not right amount of pairs: %s' %
                              (crypto['fields']['code'], fit_pairs))

    def test_crypto_fiat_pairs_fulfillment(self):
        currency_fixtures = ['currency_crypto.json',
                             'currency_tokens.json']
        currency_data = []
        for fix in currency_fixtures:
            currency_data += json.loads(open(self.path + fix).read())
        cryptos = [data for data in currency_data
                   if data['fields']['code'] not in ['RNS', 'GNT', 'QTM']]
        for crypto in cryptos:
            pair_fixture_filename = 'pairs_%s.json' % \
                                    crypto['fields']['code'].lower()
            pair_data = \
                json.loads(open(self.path + pair_fixture_filename).read())
            pairs = [pair for pair in pair_data
                     if pair['fields']['base'] == crypto['pk'] and
                     pair['fields']['quote']
                     in [4, 6, 7, 8]]  # USD, EUR, GBP and JPY
            self.assertEquals(
                len(pairs),
                4,
                'Not enough pairs for %s' % crypto['fields']['code'])

    def test_consecutive_pairs(self):
        pairs = Pair.objects.all()
        max_pk = pairs.aggregate(Max('pk'))['pk__max']
        self.assertEqual(pairs.count(), max_pk)


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
