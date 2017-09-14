from django.test import TestCase
from core.tests.base import OrderBaseTestCase
from core.models import AddressReserve, Currency, Pair, Transaction
from core.common.models import UniqueFieldMixin
from ticker.tests.base import TickerBaseTestCase
from django.core.exceptions import ValidationError
from core.tests.utils import data_provider


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
