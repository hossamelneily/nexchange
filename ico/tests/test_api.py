from ticker.tests.base import TickerBaseTestCase
from rest_framework.test import APIClient
from orders.models import Order
from unittest.mock import patch
from ico.models import Subscription, UtmSource
import os
from decimal import Decimal
from ticker.models import Price
from ico.task_summary import subscription_checker_periodic
from core.models import Currency
from referrals.models import ReferralCode, Program
from ico.task_summary import subscription_checkers, total_time_limit


class TestIcoAPI(TickerBaseTestCase):

    fixtures = TickerBaseTestCase.fixtures + [
        'program.json'
    ]

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['ETHBTC', 'BDGETH', 'ETHBDG', 'NANOETH',
                                    'ETHUSD']
        super(TestIcoAPI, cls).setUpClass()
        cls.api_client = APIClient()

    @patch.dict(os.environ, {'RPC8_PUBLIC_KEY_C1': 'xrb_nano'})
    @patch.dict(os.environ, {'RPC8_WALLET': 'to'})
    @patch.dict(os.environ, {'RPC_RPC8_PASSWORD': 'be'})
    @patch.dict(os.environ, {'RPC_RPC8_K': 'or'})
    @patch.dict(os.environ, {'RPC_RPC8_USER': 'not'})
    @patch.dict(os.environ, {'RPC_RPC8_HOST': 'to'})
    @patch.dict(os.environ, {'RPC_RPC8_PORT': 'be'})
    @patch.dict(os.environ, {'RPC7_PUBLIC_KEY_C1': '0xmain_card'})
    @patch.dict(os.environ, {'RPC_RPC7_K': 'password'})
    @patch.dict(os.environ, {'RPC_RPC7_HOST': '0.0.0.0'})
    @patch.dict(os.environ, {'RPC_RPC7_PORT': '0000'})
    def setUp(self):
        super(TestIcoAPI, self).setUp()
        # leave some upper/lower test case on this address -
        # for ETH it does not matter
        self.eth_address = '0x8116546AaC209EB58c5B531011ec42DD28EdFb71'
        self.nano_address = \
            'xrb_15gif8676odir9eonp1uppu5s3pd74arkpeqadsyp5di7zki31hr7xp86bqc'
        self.email = 'unit@test.qa'
        self.order_eth = self._create_order_api(pair_name='ETHBTC')
        self.order_bdg = self._create_order_api(pair_name='BDGETH',
                                                amount=1000)
        self.order_nano = self._create_order_api(pair_name='NANOETH',
                                                 address=self.nano_address)
        usd = Currency.objects.get(code='USD')
        usd.maximal_amount = Decimal(2000)
        usd.save()
        self.order_usd = self._create_order_api(pair_name='ETHUSD',
                                                amount=1500,
                                                amount_type='quote')
        self.order_eth.status = Order.COMPLETED
        self.order_eth.save()
        self.order_nano.status = Order.COMPLETED
        self.order_nano.save()
        self.order_bdg.status = Order.RELEASED
        self.order_bdg.save()
        self.order_usd.status = Order.RELEASED
        self.order_usd.save()
        self.assertEqual(self.order_nano.user, self.order_eth.user)

    def _create_order_api(self, pair_name='ETHBTC',
                          amount=1, address=None,
                          amount_type='base'):
        if address is None:
            address = self.eth_address
        order_data = {
            'pair': {
                'name': pair_name
            },
            'withdraw_address': {
                'address': address.lower()
            },
            'amount_{}'.format(amount_type): amount,
        }
        order_api_url = '/en/api/v1/orders/'
        res = self.api_client.post(order_api_url, order_data, format='json')
        self.assertEqual(res.status_code, 201)
        order = Order.objects.latest('id')
        return order

    def _create_subscription_api(self, address=None, ref_code='123'):
        order_data = {
            'email': self.email,
            'sending_address': address,
        }
        order_api_url = '/en/api/v1/ico/subscription/'
        # set EOS balance to zero
        self.api_client.credentials(HTTP_X_REFERRAL_TOKEN=ref_code)
        res = self.api_client.post(order_api_url, order_data, format='json')
        self.assertEqual(res.status_code, 201)
        return Subscription.objects.get(**res.json())

    @patch('web3.eth.Eth.call')
    @patch('web3.eth.Eth.getBalance')
    def test_subscription_params_checked(self, get_balance, get_token_balance):
        """ It is assumed that parameters are checkeck by invoking task
        after Subscrition is created """

        expected_balance = Decimal('11.11')
        eth = self.order_eth.pair.base
        value = int(expected_balance * Decimal('1e{}'.format(eth.decimals)))
        get_balance.return_value = value

        def side_effect(*args, expected_balance=expected_balance):
            contract_address = args[0]['to']
            token = Currency.objects.get(contract_address=contract_address)
            value = \
                int(expected_balance * Decimal('1e{}'.format(token.decimals)))
            return hex(value)

        get_token_balance.side_effect = side_effect
        expected_address_turnover = \
            self.order_eth.amount_base \
            + Price.convert_amount(self.order_bdg.amount_base, 'BDG', 'ETH') \
            + self.order_usd.amount_base
        expected_related_turnover = \
            expected_address_turnover \
            + Price.convert_amount(self.order_nano.amount_base, 'NANO', 'ETH')
        sub = self._create_subscription_api(address=self.eth_address)
        sub.refresh_from_db()
        for _order in [self.order_bdg, self.order_eth, self.order_nano]:
            self.assertIn(_order, sub.orders.all())
        self.assertEqual(sub.eth_balance, expected_balance)
        self.assertEqual(sub.address_turnover, expected_address_turnover)
        self.assertAlmostEqual(sub.related_turnover, expected_related_turnover,
                               8)
        self.assertEqual(sub.eth_currencies.count(),
                         sub.balance_set.all().count())
        total_tokens_eth_amount = Decimal('0')
        for bal in sub.balance_set.all():
            self.assertEqual(bal.balance, expected_balance)
            # we have tickers for ETH and BDG only
            if bal.currency.code in ['BDG', 'ETH']:
                self.assertAlmostEqual(
                    bal.balance_eth,
                    Price.convert_amount(
                        expected_balance, bal.currency, 'ETH'
                    ),
                    8
                )
                if bal.currency != eth:
                    total_tokens_eth_amount += bal.balance_eth
            else:
                self.assertIsNone(bal.balance_eth)
            bal.__str__()
        self.assertEqual(sub.tokens_balance_eth, total_tokens_eth_amount)
        self.assertEqual(sub.tokens_count, sub.eth_currencies.count() - 1,
                         'all except ETH')
        # set EOS balance to zero
        self.assertEqual(sub.tokens_count, sub.eth_currencies.count() - 1,
                         'all except ETH')
        bal = sub.balance_set.get(currency__code='EOS')
        bal.balance = Decimal('0')
        bal.save()
        sub.refresh_from_db()
        self.assertEqual(sub.tokens_count, sub.eth_currencies.count() - 2,
                         'all except ETH and EOS')
        #
        empty_sub = self._create_subscription_api()
        empty_sub.refresh_from_db()
        self.assertIsNone(empty_sub.sending_address)
        with patch('ico.tasks.generic.eth_balance_checker.'
                   'EthBalanceChecker.run') as bal:
            subscription_checker_periodic.apply_async()
            bal.assert_called_once()
        with patch('ico.tasks.generic.address_turnover_checker.'
                   'AddressTurnoverChecker.run') as turn:
            subscription_checker_periodic.apply_async()
            turn.assert_called_once()
        with patch('ico.tasks.generic.related_turnover_checker.'
                   'RelatedTurnoverChecker.run') as turn:
            subscription_checker_periodic.apply_async()
            turn.assert_called_once()
        with patch('ico.tasks.generic.token_balance_checker.'
                   'TokenBalanceChecker.run') as bal:
            subscription_checker_periodic.apply_async()
            bal.assert_called_once()

        # check category
        names = [c.name for c in sub.category.all()]
        self.assertIn('FIAT', names)
        self.assertIn('FIAT RELEASED', names)
        self.assertIn('FIAT (>1000USD)', names)
        self.assertIn('FIAT (>500USD)', names)
        self.assertIn('FIAT (>100USD)', names)
        self.assertEqual(len(names), 5)

    def test_set_utm_source(self):
        program = Program.objects.get(pk=1)
        code = ReferralCode(user=self.user, program=program)
        code.save()
        utm_source = UtmSource(name='Ya Olde Gypsy Tavern')
        utm_source.save()
        utm_source.referral_codes.add(code)
        sub = self._create_subscription_api(
            address=self.eth_address,
            ref_code=code.code
        )
        sub.refresh_from_db()
        self.assertEqual(sub.referral_code, code)
        self.assertEqual(sub.utm_source, utm_source)
        names = [c.name for c in sub.category.all()]
        self.assertIn('REFEREES', names)
        self.assertIn('FIAT', names)
        self.assertIn('FIAT RELEASED', names)
        self.assertIn('FIAT (>1000USD)', names)
        self.assertIn('FIAT (>500USD)', names)
        self.assertIn('FIAT (>100USD)', names)
        self.assertEqual(len(names), 6)

    def test_check_periodic_countdown(self):
        address_int = int(self.eth_address, 16)
        for i in range(address_int, address_int + 10):
            self._create_subscription_api(hex(i))
        subs_count = Subscription.objects.filter(
            sending_address__isnull=False).count()
        with patch('celery.app.task.Task.apply_async') as apply_async:
            subscription_checker_periodic()
            _prev_countdown = _final_countdown = 0
            _prev_id = address_int
            _prev_time_limit = 0
            for i, _args in enumerate(apply_async.call_args_list):
                _coutdown = _args[1].get('countdown', 0)
                _id = _args[0][0][0]
                self.assertLessEqual(_prev_countdown, _coutdown)
                self.assertEqual(_coutdown, _prev_countdown + _prev_time_limit)
                self.assertLessEqual(_id, _prev_id)
                _prev_countdown = _final_countdown = _coutdown
                _prev_id = _id
                _prev_time_limit = subscription_checkers[
                    i % len(subscription_checkers)
                ].time_limit
            expected_final_countdown = \
                total_time_limit * (subs_count - 1) \
                + sum([t.time_limit for t in subscription_checkers[:-1]])
            self.assertEqual(_final_countdown, expected_final_countdown)
