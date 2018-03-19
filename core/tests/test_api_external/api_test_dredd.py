import sys

from django.contrib.auth.models import User
from accounts.task_summary import renew_cards_reserve_invoke
from orders.models import Order
from django.contrib.staticfiles.testing import LiveServerTestCase
from core.tests.base import TransactionImportBaseTestCase, OrderBaseTestCase
from referrals.models import ReferralCode, Referral
from ticker.tests.base import TickerBaseTestCase
import requests_mock
from subprocess import call
from django.core.urlresolvers import reverse
from django.test import Client
from oauth2_provider.models import AccessToken
from datetime import timedelta
from django.utils import timezone


class DreddTestAPI(LiveServerTestCase, TransactionImportBaseTestCase,
                   TickerBaseTestCase):

    fixtures = OrderBaseTestCase.fixtures + [
        'program.json'
    ]

    def setUp(self):
        self.DISABLE_NON_MAIN_PAIRS = False
        super(DreddTestAPI, self).setUp()
        self.url = self.live_server_url
        with requests_mock.mock() as mock:
            self._mock_cards_reserve(mock)
            renew_cards_reserve_invoke.apply()

        # This is for matching example data on apiary.apib
        self.create_user()
        self._create_order()
        self.order.unique_reference = 'V08PD'
        self.order.save()
        self.create_referral()

    def create_referral(self):
        code = 'dredd_test'
        referee = User.objects.exclude(pk=self.user.pk).first()
        referral_code = ReferralCode(code=code, user=self.user)
        referral_code.save()
        referral = Referral(referee=referee, code=referral_code)
        referral.save()
        self._create_order(user=referee)
        self.order.status = Order.COMPLETED
        self.order.save()

    def create_user(self):
        # FIXME: Please refactor me!
        self.logout_url = reverse('accounts.logout')
        self.username = 'demo'
        self.password = 'je^?@e~xp{K%"y#'
        self.data = \
            {
                'first_name': 'Demo',
                'last_name': 'Demo',
                'email': 'demo@onit.ws',
            }

        # this is used to identify addresses created by allocate_wallets mock
        self.address_id_pattern = 'addr_id_'
        self._mock_rpc()
        self._mock_uphold()
        self.create_main_user()

        self.client = Client()
        success = self.client.login(username=self.username,
                                    password=self.password)
        expires = timezone.now() + timedelta(days=30)
        token = AccessToken(
            user=self.user,
            token='3HrghbVeDUQWaOriqrXYLZmCb4cEXB',
            expires=expires
        )
        token.save()
        assert success

    def test_dredd(self):
        exit_status = call(['./node_modules/.bin/dredd', 'apiary.apib',
                            self.url])
        if exit_status == 1:
            sys.exit(1)
