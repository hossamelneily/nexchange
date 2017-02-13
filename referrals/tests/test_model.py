from random import randint
from decimal import Decimal

from core.tests.base import OrderBaseTestCase

from orders.models import Order
from referrals.models import ReferralCode, Referral, Program


class TestReferralModel(OrderBaseTestCase):
    fixtures = OrderBaseTestCase.fixtures + [
        'program.json'
    ]

    def __init__(self, *args, **kwargs):
        self.amount_coin_base = 0.1
        self.amount_coin_multiplier = 10
        self.total_orders = 20
        self.orders = []
        self.test_subjects = 3
        self.referral = None
        self.revenue = None
        self.turnover = Decimal('0.0')
        super(TestReferralModel, self).__init__(*args, **kwargs)

    def setUp(self):
        super(TestReferralModel, self).setUp()
        program = Program.objects.get(pk=1)
        code = ReferralCode(user=self.user, program=program)
        code.save()
        # in real life middleware checks that
        # referee and referrer are not the same person
        self.referral = Referral(code=code, referee=self.user)
        self.referral.save()
        for i in range(10):
            rand_coin = self.amount_coin_base * \
                randint(1, self.amount_coin_multiplier)
            order = Order(
                user=self.user,
                amount_base=rand_coin,
                pair=self.BTCEUR
            )
            order.save()
            self.orders.append(order)

        for i in range(self.test_subjects):
            order = self.orders[i]
            order.status = Order.COMPLETED
            order.save()
            self.turnover += Decimal(order.amount_base)

        self.revenue = self.turnover * \
            self.referral.program.percent_first_degree

    def test_count_active(self):
        self.assertEqual(self.test_subjects,
                         self.referral.confirmed_orders_count)

    def test_not_count_active_if_program_exceed(self):
        pass

    def test_revenue(self):
        self.assertEqual(round(self.revenue, 8),
                         self.referral.revenue)

    def test_not_revenue_active_if_program_exceed(self):
        pass

    def test_turnover(self):
        self.assertEqual(round(self.turnover, 8),
                         self.referral.turnover)

    def test_not_turnover_active_if_program_exceed(self):
        pass

    def test_completed_added_to_balance(self):
        pass

    def test_not_added_to_balance_if_program_exceed(self):
        pass

    def obeys_ppl_limit(self):
        pass

    def test_obeys_volume_limit(self):
        pass

    def test_obeys_lifespan_limit(self):
        pass

    # MIDDLEWARE STUFF
    def test_cannot_refer_self(self):
        pass

    def can_refer_new_user(self):
        pass

    def can_refer_old_empty_user(self):
        pass

    def cannot_refer_active_user(self):
        pass

    def cannot_be_referred_by_two_users(self):
        pass
