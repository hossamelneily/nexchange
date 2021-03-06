from random import randint
from decimal import Decimal

from core.models import Pair, Currency
from orders.models import Order
from referrals.models import ReferralCode, Referral, Program
from core.tests.base import OrderBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from ticker.models import Price
from accounts.models import Balance
from unittest import skip


class TestReferralModel(TickerBaseTestCase):
    fixtures = OrderBaseTestCase.fixtures + [
        'program.json'
    ]

    def __init__(self, *args, **kwargs):
        self.amount_coin_base = 0.1
        self.amount_coin_multiplier = 10
        self.total_orders = 20
        self.orders = []
        self.test_subjects = 5
        self.referral = None
        self.revenue = None
        self.withdrawals = 0

        self.turnover = Decimal('0.0')
        super(TestReferralModel, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['BTCLTC', 'LTCBTC']
        super(TestReferralModel, cls).setUpClass()

    def setUp(self):
        super(TestReferralModel, self).setUp()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()
        program = Program.objects.get(pk=1)
        code = ReferralCode(user=self.user, program=program)
        code.save()
        # in real life middleware checks that
        # referee and referrer are not the same person
        self.referral = Referral(code=code, referee=self.user)
        self.referral.save()

        def get_rand_int(): return randint(1, self.amount_coin_multiplier)  # noqa

        for i in range(10):
            rand_coin = self.amount_coin_base * get_rand_int()
            order = Order(
                user=self.user,
                amount_base=rand_coin,
                pair=self.BTCEUR
            )
            order.save()
            self.orders.append(order)

        for i in range(self.test_subjects):
            order = self.orders[i]
            intermediate_withdrawal = round(get_rand_int() * Decimal(0.001), 8)
            order.status = Order.COMPLETED
            order.save()

            balance = Balance.objects.get(user=self.user)
            balance.balance -= intermediate_withdrawal
            balance.save()

            self.withdrawals += intermediate_withdrawal
            self.turnover += Decimal(order.amount_base)

        self.revenue = round(
            self.turnover *
            Decimal(
                self.referral.program.percent_first_degree),
            8)

    def test_count_active(self):
        self.assertEqual(self.test_subjects,
                         self.referral.confirmed_orders_count)

    @skip('TODO test')
    def test_not_count_active_if_program_exceed(self):
        pass

    def test_revenue(self):
        self.assertEqual(round(self.revenue, 8),
                         self.referral.revenue)

    @skip('TODO test')
    def test_not_revenue_active_if_program_exceed(self):
        pass

    def test_turnover(self):
        self.assertEqual(round(self.turnover, 8),
                         self.referral.turnover)

    def test_partial_turnover(self):
        amount_base = Decimal('11.11')
        pair = Pair.objects.get(name='LTCBTC')
        rate = Price.objects.filter(pair__name='BTCLTC').last().ticker.rate
        other_turnover = amount_base / rate
        self.assertEqual(0, self.referral.turnover_other_currencies_in_btc)
        order = Order(
            user=self.user,
            amount_base=amount_base,
            pair=pair,
            status=Order.COMPLETED
        )
        order.save()
        self.assertEqual(round(self.turnover, 8),
                         self.referral.turnover_btc)
        self.assertEqual(round(other_turnover, 8),
                         self.referral.turnover_other_currencies_in_btc)
        self.assertEqual(self.referral.turnover,
                         self.referral.turnover_other_currencies_in_btc +
                         self.referral.turnover_btc)

    def test_correct_balance(self):
        balance = Balance.objects.get(user=self.user)
        adapted_balance = self.revenue - self.withdrawals
        self.assertNotEqual(self.revenue, balance.balance)
        self.assertEqual(adapted_balance, balance.balance)

    @skip('TODO test')
    def test_not_turnover_active_if_program_exceed(self):
        pass

    @skip('TODO test')
    def test_completed_added_to_balance(self):
        pass

    @skip('TODO test')
    def test_not_added_to_balance_if_program_exceed(self):
        pass

    @skip('TODO test')
    def obeys_ppl_limit(self):
        pass

    @skip('TODO test')
    def test_obeys_volume_limit(self):
        pass

    @skip('TODO test')
    def test_obeys_lifespan_limit(self):
        pass

    # MIDDLEWARE STUFF
    @skip('TODO test')
    def test_cannot_refer_self(self):
        pass

    @skip('TODO test')
    def can_refer_new_user(self):
        pass

    @skip('TODO test')
    def can_refer_old_empty_user(self):
        pass

    @skip('TODO test')
    def cannot_refer_active_user(self):
        pass

    @skip('TODO test')
    def cannot_be_referred_by_two_users(self):
        pass
