from random import randint
from decimal import Decimal
import requests_mock

from core.models import Pair, Currency
from orders.models import Order
from referrals.models import ReferralCode, Referral, Program
from core.tests.base import OrderBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from ticker.models import Price
from accounts.models import Balance
from unittest import skip
from rest_framework.test import APIClient


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

    def setUp(self):
        self.ENABLED_TICKER_PAIRS = ['BTCLTC', 'LTCBTC']
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
        self.api_client = APIClient()

    def _create_order_api(self, name='ETHLTC', ref_code='123'):
        order_data = {
            "amount_base": 3,
            "is_default_rule": False,
            "pair": {
                "name": name
            },
            "withdraw_address": {
                "address": "0x77454e832261aeed81422348efee52d5bd3a3684"
            }
        }
        self.api_client.credentials(HTTP_X_REFERRAL_TOKEN=ref_code)
        order_api_url = '/en/api/v1/orders/'
        response = self.api_client.post(order_api_url, order_data,
                                        format='json')
        order = Order.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        return order

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

    @requests_mock.mock()
    def test_partial_turnover(self, mock):
        self.get_tickers(mock)
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

    @skip('saving time because test is not implemented yet')
    def test_not_turnover_active_if_program_exceed(self):
        pass

    @skip('saving time because test is not implemented yet')
    def test_completed_added_to_balance(self):
        pass

    @skip('saving time because test is not implemented yet')
    def test_not_added_to_balance_if_program_exceed(self):
        pass

    @skip('saving time because test is not implemented yet')
    def obeys_ppl_limit(self):
        pass

    @skip('saving time because test is not implemented yet')
    def test_obeys_volume_limit(self):
        pass

    @skip('saving time because test is not implemented yet')
    def test_obeys_lifespan_limit(self):
        pass

    # MIDDLEWARE STUFF
    @skip('saving time because test is not implemented yet')
    def test_cannot_refer_self(self):
        pass

    @skip('saving time because test is not implemented yet')
    def can_refer_new_user(self):
        pass

    @skip('saving time because test is not implemented yet')
    def can_refer_old_empty_user(self):
        pass

    @skip('saving time because test is not implemented yet')
    def cannot_refer_active_user(self):
        pass

    @skip('saving time because test is not implemented yet')
    def cannot_be_referred_by_two_users(self):
        pass

    def test_different_curr_balance(self):
        balance_currency = 'ETH'
        balances = Balance.objects.filter(user=self.user)
        for balance in balances:
            balance.balance = Decimal('0')
            balance.save()
        referral_code = self.user.referral_code.last()
        old_refs_count = referral_code.referral_set.filter(
            code=referral_code
        ).count()
        order = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=referral_code.code
        )
        order.status = Order.COMPLETED
        order.save()
        Referral.objects.filter()
        self.assertEqual(
            old_refs_count + 1,
            referral_code.referral_set.filter(code=referral_code).count()
        )
        referral = referral_code.referral_set.latest('pk')
        balances = Balance.objects.filter(user=self.user)
        for balance in balances:
            if balance.currency.code == balance_currency:
                self.assertEqual(
                    balance.balance,
                    order.amount_base * referral.referral_percent
                )
                self.assertAlmostEqual(
                    referral.revenue,
                    balance.balance / Price.get_rate('BTC', 'ETH'),
                    8
                )
            else:
                self.assertEqual(balance.balance, Decimal('0'))
