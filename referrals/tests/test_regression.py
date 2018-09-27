from orders.models import Order
from referrals.models import ReferralCode, Program, Referral
from core.tests.base import OrderBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from unittest.mock import patch
from rest_framework.test import APIClient
from django.db import IntegrityError
from oauth2_provider.models import AccessToken
from oauthlib.common import generate_token
from datetime import timedelta
from django.utils import timezone
from django.conf import settings


class TestReferralRegression(TickerBaseTestCase):
    fixtures = OrderBaseTestCase.fixtures + [
        'program.json'
    ]

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = ['ETHLTC', 'BTCETH']
        super(TestReferralRegression, cls).setUpClass()
        cls.api_client = APIClient()

    def setUp(self):
        super(TestReferralRegression, self).setUp()
        program = Program.objects.get(pk=1)
        self.code = ReferralCode(user=self.user, program=program)
        self.code.save()

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

    @patch('referrals.middleware.get_client_ip')
    def test_create_referrals_diff_users_same_ip(self, get_ip):
        ip = get_ip.return_value = '123'
        balance_currency = 'ETH'
        order1 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=self.code.code
        )
        self.assertEqual(self.code.code, order1.referred_with.code)
        self.api_client.logout()
        order2 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=self.code.code
        )
        order1.status = Order.COMPLETED
        order2.status = Order.COMPLETED
        order1.save()
        order2.save()
        self.assertNotEqual(order1.user, order2.user)
        self.assertEqual(
            2,
            self.code.referral_set.filter(code=self.code,
                                          ip=ip).count(),
            'Two referrals must be created'
        )

    @patch('referrals.middleware.get_client_ip')
    def test_create_only_one_referral_per_user(self, get_ip):
        code2 = ReferralCode(user=self.user, program=self.code.program)
        code2.save()
        self.assertNotEqual(self.code.code, code2.code)
        balance_currency = 'ETH'
        get_ip.return_value = '123'
        order1 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=self.code.code
        )
        get_ip.return_value = '456'
        order2 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=code2.code
        )
        self.assertEqual(order1.user, order2.user)
        self.assertEqual(
            1,
            self.code.referral_set.filter(code=self.code).count(),
            'First referral must be created'
        )
        self.assertEqual(
            0,
            code2.referral_set.filter(code=code2).count(),
            'Second referral cannot be created'
        )
        order1.status = Order.COMPLETED
        order2.status = Order.COMPLETED
        order1.save()
        order2.save()
        referral = self.code.referral_set.get()
        self.assertEqual(referral.orders.count(), 2)
        user = order1.user
        with self.assertRaises(IntegrityError):
            Referral.objects.get_or_create(referee=user, code=code2)
        self.assertEqual(
            1,
            Referral.objects.filter(referee=user).count(),
            'One Referral total'
        )

    @patch('referrals.middleware.get_client_ip')
    def test_referral_api_shows_order_ref_list(self, get_ip):
        get_ip.return_value = '123'
        balance_currency = 'ETH'
        order1 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=self.code.code
        )
        order2 = self._create_order_api(
            name='{}LTC'.format(balance_currency),
            ref_code=self.code.code
        )
        order1.status = Order.COMPLETED
        order1.save()
        order2.status = Order.COMPLETED
        order2.save()
        expires_in = settings.ACCESS_TOKEN_EXPIRE_SECONDS
        expires = timezone.now() + timedelta(seconds=expires_in)
        _token = generate_token()
        token = AccessToken(
            user=self.user,
            token=_token,
            expires=expires
        )
        token.save()
        self.api_client.logout()
        res_unauth = self.api_client.get('/en/api/v1/referrals/')
        self.assertEqual(res_unauth.status_code, 401)
        self.api_client.credentials(
            Authorization="Bearer {}".format(_token)
        )
        res = self.api_client.get('/en/api/v1/referrals/')
        refs = [o['unique_reference'] for o in res.json()[0]['orders']]
        self.assertIn(
            order1.unique_reference, refs
        )
        self.assertIn(
            order2.unique_reference, refs
        )
