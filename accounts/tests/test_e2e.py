from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from freezegun import freeze_time

from accounts.models import SmsToken
from core.tests.base import UserBaseTestCase
from core.tests.utils import passive_authentication_helper, data_provider


class LoginEndToEndTestCase(UserBaseTestCase):

    @data_provider(
        lambda: (('+79259737305',),
                 ('79259737306',),
                 ('0079259737307',),
                 ('+16464612877',)))
    @patch('accounts.decoratos.get_google_response')
    @patch('nexchange.utils.TwilioRestClient')
    def test_reuse_sms_token(self, uname, rest_client, verify_captcha):
        verify_captcha.return_value = True
        rest_client.return_value = MagicMock()
        url = reverse('accounts.user_by_phone')
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 0)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        not_expired_time = datetime.now() + settings.SMS_TOKEN_VALIDITY - \
            timedelta(minutes=1)
        with freeze_time(not_expired_time, tick=False):
            asserted_from_phone = \
                settings.TWILIO_PHONE_FROM_US if \
                uname.startswith('+1') else settings.TWILIO_PHONE_FROM_UK
            user = User.objects.last()
            token = SmsToken.objects.last()
            msg = settings.SMS_MESSAGE_AUTH + '{}'.format(token.sms_token)
            rest_client.assert_called_once_with(settings.TWILIO_ACCOUNT_SID,
                                                settings.TWILIO_AUTH_TOKEN)
            rest_client.return_value.messages.create.assert_called_once_with(
                body=msg, to=user.username,
                from_=asserted_from_phone)

            passive_authentication_helper(
                self.client,
                user,
                token.sms_token,
                user.username,
                False
            )

            self.assertTrue(user.is_authenticated())
