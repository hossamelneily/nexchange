from core.tests.base import UserBaseTestCase
from django.urls import reverse
from json import loads
from core.tests.utils import data_provider


class ReferralCodeTestCase(UserBaseTestCase):

    def setUp(self):
        super(ReferralCodeTestCase, self).setUp()
        # one referral code is created on first profile save
        self.user.profile.save()

    @data_provider(lambda: (
        ('first_code', 'OK', 1, 'Create first code'),
        ('first_code', 'ERROR', 0, 'Try to repeat same code'),
        (None, 'OK', 1, 'New code random code'),
    ))
    def test_create_new_code(self, code, status, new_codes_count, case_name):
        if code is not None:
            data = {'code_new': code}
        else:
            data = {}
        before_codes = len(self.user.referral_code.all())
        response = self.client.post(reverse('referrals.code_new'), data)
        content = loads(str(response.content, encoding='utf-8'))
        after_codes = len(self.user.referral_code.all())
        self.assertEqual(before_codes + new_codes_count, after_codes,
                         case_name)
        if code is not None:
            self.assertEqual(code, self.user.referral_code.last().code,
                             case_name)
        self.assertEqual(content['status'], status, case_name)
