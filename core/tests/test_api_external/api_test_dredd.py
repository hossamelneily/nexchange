import sys

from django.contrib.auth.models import User
from accounts.task_summary import renew_cards_reserve_invoke
from orders.models import Order
from core.tests.base import TransactionImportBaseTestCase, OrderBaseTestCase,\
    NexchangeLiveServerTestCase
from referrals.models import ReferralCode, Referral
from ticker.tests.base import TickerBaseTestCase
from subprocess import call
from django.urls import reverse
from oauth2_provider.models import AccessToken
from datetime import timedelta
from django.utils import timezone
from core.tests.base import NexchangeClient


class DreddTestAPI(NexchangeLiveServerTestCase, TransactionImportBaseTestCase,
                   TickerBaseTestCase):

    fixtures = OrderBaseTestCase.fixtures + [
        'program.json'
    ]

    @classmethod
    def setUpClass(cls):
        cls.DISABLE_NON_MAIN_PAIRS = False
        super(DreddTestAPI, cls).setUpClass()
        renew_cards_reserve_invoke.apply()
        cls.url = cls.live_server_url

    def setUp(self):
        super(DreddTestAPI, self).setUp()
        # This is for matching example data on apiary.apib
        self.create_user()
        self._create_order(pair_name='ETHLTC')
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

        self.client = NexchangeClient()
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

    def test_dredd_private(self):
        exit_status = call(
            ['./node_modules/.bin/dredd', 'apiary-private.apib', self.url]
        )
        if exit_status == 1:
            sys.exit(1)
