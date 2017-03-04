import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from freezegun import freeze_time

from accounts.models import Profile, SmsToken
from core.tests.base import UserBaseTestCase
from core.tests.utils import passive_authentication_helper, data_provider


class RegistrationTestCase(TestCase):

    def setUp(self):
        self.data = {
            'phone': '+555190909891',
            'password1': '123Mudar',
            'password2': '123Mudar',
        }
        self.user = None
        super(RegistrationTestCase, self).setUp()

    def tearDown(self):
        if self.user:
            self.user.delete()

    def test_can_register(self):
        response = self.client.post(
            reverse('accounts.register'), self.data)

        # Redirect is to user profile Page
        self.assertEqual(302, response.status_code)
        self.assertEqual(reverse('accounts.user_profile'), response.url)
        # Saved data Ok
        user = User.objects.last()
        self.assertEqual(self.data['phone'], user.profile.phone)

    def test_cannot_register_existent_phone(self):
        # Creates first with the phone
        self.client.post(
            reverse('accounts.register'),
            self.data
        )

        # ensure is created
        self.assertIsInstance(
            Profile.objects.get(phone=self.data['phone']), Profile)

        response = self.client.post(
            reverse('accounts.register'), self.data)

        self.assertFormError(response, 'profile_form', 'phone',
                             'This phone is already registered.')


class ProfileUpdateTestCase(UserBaseTestCase):

    def test_can_update_profile(self):
        response = self.client.post(
            reverse('accounts.user_profile'), self.data)
        # Redirect after update
        self.assertEqual(302, response.status_code)

        # saved the User instance data
        user = User.objects.get(email=self.data['email'])
        self.assertEqual(
            user.profile.first_name,
            self.data['first_name']
        )  # saved the profile too
        self.assertEqual(user.profile.last_name, self.data['last_name'])

    def test_phone_verification_with_success(self, phone=None):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = sms_token.sms_token

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.user.username,
            True
        )

        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        response = json.loads(
            str(response.content, encoding='utf8')
        )
        self.assertEquals('OK', response['status'])

        # Ensure profile was enabled
        self.assertFalse(user.profile.disabled)

    def test_phone_verification_fails_with_wrong_token(self, phone=None):
        # incorrect token
        token = "{}XX".format(SmsToken.get_sms_token())

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.user.username,
            True
        )
        # Ensure the token was correctly received
        self.assertEqual(400, response.status_code)
        response = json.loads(
            str(response.content, encoding='utf8')
        )
        self.assertEquals('Error', response['status'])

    def test_phone_verification_with_success_logged_out(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = sms_token.sms_token
        self.client.get(self.logout_url)
        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.user.username,
            False
        )

        # Ensure the token was correctly received
        self.assertEqual(201, response.status_code)
        response = json.loads(
            str(response.content, encoding='utf8')
        )
        self.assertEquals('OK', response['status'])

        # Ensure profile was enabled
        self.assertFalse(user.profile.disabled)

    def test_phone_verification_with_failure_logged_out_without_phone(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = sms_token.sms_token

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            None,
            False
        )

        # Ensure the token was correctly received
        self.assertEqual(400, response.status_code)

        # Ensure profile was not enabled
        self.assertTrue(user.profile.disabled)

    def test_phone_verification_fails_with_wrong_token_logged_out_no_phone(
            self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = '{}xx'.format(sms_token.sms_token)

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            None,
            False
        )

        # Ensure the token was correctly received
        self.assertEqual(400, response.status_code)

        # Ensure profile was not enabled
        self.assertTrue(user.profile.disabled)

    @data_provider(lambda: (('xx', 201, False), ('12', 400, True),))
    def test_phone_verification_token_logged_out_with_phone(
            self, token_addition, status_code, profile_disabled):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = '{}{}'.format(sms_token.sms_token,
                              token_addition)

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.username,
            False
        )

        # Ensure the token was correctly received
        self.assertEqual(status_code, response.status_code)

        # Ensure profile was not enabled
        self.assertEqual(profile_disabled, user.profile.disabled)

    def test_phone_verification_success_with_spaces_in_token(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = ' {} '.format(sms_token.sms_token)

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.user.username,
            False
        )

        # Ensure the token was correctly received
        self.assertEqual(201, response.status_code)

        # Assert that profile was activated
        self.assertFalse(self.user.profile.disabled)


class ProfileFindTestCase(UserBaseTestCase):

    def setUp(self):
        super(ProfileFindTestCase, self).setUp()

        self.profile = Profile()
        self.profile.user = self.user
        self.profile.save()

    def test_finds_profile_by_natural_key(self):
        natural_key = self.user.profile.natural_key()

        profile = Profile.objects.get_by_natural_key(natural_key)
        self.assertEqual(profile, self.profile)


class LoginTestCase(UserBaseTestCase):

    def test_login_should_display_correctly(self):
        # setup
        self.client.logout()
        response = self.client.get(reverse('accounts.login'))

        # tests
        self.assertEqual(response.status_code, 200)

        # teardown
        self.client.login(username=self.user.username, password='password')

    def test_login_should_log_in_user(self):
        # setup
        self.client.logout()
        response = self.client.post(reverse('accounts.login'), {
            'username': self.user.username,
            'password': self.password
        }, follow=True)

        # tests
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['request'].user, self.user)


class LogoutTestCase(UserBaseTestCase):

    def test_logout_should_log_out_user(self):
        # setup
        response = self.client.get(reverse('accounts.logout'), follow=True)

        # tests
        self.assertNotEqual(response.context['request'].user, self.user)

        # teardown
        self.client.login(username=self.user.username, password='password')


class PassiveAuthenticationTestCase(UserBaseTestCase):

    def __init__(self, *args, **kwargs):
        self.token = None
        self.user = None
        super(PassiveAuthenticationTestCase,
              self).__init__(*args, **kwargs)

    def setUp(self):
        super(PassiveAuthenticationTestCase, self).setUp()
        patcher = patch('accounts.decoratos.get_google_response',
                        return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        if self.user:
            self.user.delete()
        if self.token:
            self.token.delete()

    def test_already_logged_in(self):
        uname = '+79259737305'
        url = reverse('accounts.user_by_phone')
        payload = {
            'phone': uname,
        }

        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 403)

    @patch('accounts.views.send_auth_sms')
    def test_sms_sent_success(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '+79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)

        self.assertEquals(res.status_code, 200)
        users = User.objects.filter(username=uname)

        self.assertEquals(len(users), 1)
        self.user = users[0]

        sms_token = SmsToken.objects.\
            filter(user=self.user).last()
        self.assertTrue(sms_token)

        send_sms.assert_called_once_with(self.user)

    @patch('accounts.views.send_auth_sms')
    def test_user_create_once(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '+79259737305'
        payload = {
            'phone': uname,
        }
        # create once
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        # attempt to create twice
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        users = User.objects.filter(username=uname)

        self.assertEquals(len(users), 1)
        self.user = users[0]

        sms_token = SmsToken.objects.\
            filter(user=self.user).last()
        self.assertTrue(sms_token)

        self.assertEqual(2, send_sms.call_count)

    # regression!
    @patch('accounts.views.send_auth_sms')
    def test_user_login_2nd_time(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '+79259737305'
        payload = {
            'phone': uname,
        }
        # create once
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        # attempt to create twice
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        users = User.objects.filter(username=uname)

        self.assertEquals(len(users), 1)
        self.user = users[0]

        sms_token = SmsToken.objects.\
            filter(user=self.user).last()
        self.assertTrue(sms_token)

        self.assertEqual(2, send_sms.call_count)

        token = SmsToken.objects.last()
        url = reverse('accounts.verify_phone')
        payload = {
            'token': token.sms_token,
            'phone': self.user.username
        }
        res = self.client.post(url, data=payload)
        # make attacker think phone is always created
        self.assertEqual(201, res.status_code)
        self.assertTrue(self.user.is_authenticated())

        res = self.client.post(url, data=payload)
        # user is already logged in!
        self.assertEqual(400, res.status_code)

    @patch('accounts.views.send_auth_sms')
    def test_creates_sms_token(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 0)
        creation_time = datetime.now()
        with freeze_time(creation_time, tick=False):
            tokens_before_len = SmsToken.objects.all().count()
            res = self.client.post(url, data=payload)
            self.assertEquals(res.status_code, 200)

            formatted_uname = '{}{}'.format(
                settings.PLUS_INTERNATIONAL_PREFIX, uname)
            users = User.objects.filter(username=formatted_uname)

            tokens = SmsToken.objects.all()
            tokens_after_len = tokens.count()
            last_token = tokens.last()

        self.assertEqual(
            last_token.created_on.timestamp(),
            creation_time.timestamp())
        self.assertEqual(users[0], last_token.user)
        self.assertEqual(tokens_before_len + 1, tokens_after_len)

    @patch('nexchange.utils.TwilioRestClient')
    def test_reuse_sms_token(self, rest_client):
        rest_client.return_value = MagicMock()
        url = reverse('accounts.user_by_phone')
        uname = '79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 0)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        before_last_tokens = SmsToken.objects.all()
        before_last_token = before_last_tokens.last()
        len_before = before_last_tokens.count()
        not_expired_time = datetime.now() + settings.SMS_TOKEN_VALIDITY - \
            timedelta(minutes=1)
        with freeze_time(not_expired_time, tick=False):
            res = self.client.post(url, data=payload)
            self.assertEquals(res.status_code, 200)

            formatted_uname = '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX,
                                            uname)
            users = User.objects.filter(username=formatted_uname)

            tokens_after = SmsToken.objects.all()
            last_token = tokens_after.last()
            len_after = tokens_after.count()

        self.assertEqual(last_token,
                         before_last_token)
        self.assertEqual(users[0], last_token.user)
        self.assertEqual(len_before,
                         len_after)

    @patch('nexchange.utils.TwilioRestClient')
    def test_expire_sms_token(self, rest_client):
        rest_client.return_value = MagicMock()
        url = reverse('accounts.user_by_phone')
        uname = '79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 0)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)

        before_last_tokens = SmsToken.objects.all()
        before_last_token = before_last_tokens.last()
        before_len = before_last_tokens.count()
        expired_time = datetime.now() + settings.SMS_TOKEN_VALIDITY + \
            timedelta(seconds=5)

        with freeze_time(expired_time, tick=False):

            res = self.client.post(url, data=payload)
            self.assertEquals(res.status_code, 200)

            formatted_uname = '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX,
                                            uname)
            users = User.objects.filter(username=formatted_uname)

            tokens_after = SmsToken.objects.all()
            last_token = tokens_after.last()
            after_len = tokens_after.count()

        self.assertNotEqual(last_token,
                            before_last_token)
        self.assertNotEqual(last_token.created_on.timestamp(),
                            before_last_token.created_on.timestamp())
        self.assertEqual(users[0], last_token.user)
        self.assertEqual(before_len + 1,
                         after_len)

    @patch('nexchange.utils.TwilioRestClient')
    def test_call_twillio_api(self, rest_client):
        rest_client.return_value = MagicMock()
        url = reverse('accounts.user_by_phone')
        uname = '+79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 1)
        last_token = SmsToken.objects.filter(user=users[0]).latest('id')
        msg = settings.SMS_MESSAGE_AUTH + "{}".format(last_token.sms_token)
        rest_client.assert_called_once_with(settings.TWILIO_ACCOUNT_SID,
                                            settings.TWILIO_AUTH_TOKEN)
        rest_client.return_value.messages.\
            create.assert_called_once_with(body=msg, to=uname,
                                           from_=settings.TWILIO_PHONE_FROM_UK)

    @patch('nexchange.utils.TwilioRestClient')
    def test_call_twillio_api_us(self, rest_client):
        rest_client.return_value = MagicMock()
        url = reverse('accounts.user_by_phone')
        uname = '+15005550001'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        users = User.objects.filter(username=uname)
        res = self.client.post(url, data=payload)
        self.assertEquals(res.status_code, 200)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 1)
        last_token = SmsToken.objects.filter(user=users[0]).latest('id')
        msg = settings.SMS_MESSAGE_AUTH + "{}".format(last_token.sms_token)
        rest_client.assert_called_once_with(settings.TWILIO_ACCOUNT_SID,
                                            settings.TWILIO_AUTH_TOKEN)
        rest_client.return_value.messages.\
            create.assert_called_once_with(body=msg, to=uname,
                                           from_=settings.TWILIO_PHONE_FROM_US)

    @patch('accounts.views.send_auth_sms')
    def test_creates_profile(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '79259737399'
        payload = {
            'phone': uname,
        }
        creation_time = datetime.now()
        with freeze_time(creation_time, tick=False):
            self.client.get(self.logout_url)
            users = User.objects.filter(username=uname)
            self.assertEquals(len(users), 0)
            res = self.client.post(url, data=payload)
            self.assertEquals(res.status_code, 200)

            formatted_uname = '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX,
                                            uname)
            users = User.objects.filter(username=formatted_uname)

            profile = Profile.objects.filter(
                user=users[0],
            )

        self.assertEqual(1, len(profile))
        self.assertEqual(formatted_uname, str(profile[0].phone))
        self.assertEqual(
            creation_time.timestamp(),
            profile[0].created_on.timestamp())

    @patch('accounts.views.send_auth_sms')
    def test_sms_adds_plus(self, send_sms):
        url = reverse('accounts.user_by_phone')
        uname = '79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)

        self.assertEquals(res.status_code, 200)
        users = User.objects.filter(username=uname)
        self.assertEquals(len(users), 0)

        formatted_uname = '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX,
                                        uname)
        users = User.objects.filter(username=formatted_uname)
        self.assertEquals(len(users), 1)
        self.user = users[0]

        sms_token = SmsToken.objects.\
            filter(user=self.user).last()
        self.assertTrue(sms_token)
        self.assertEqual(formatted_uname,
                         self.user.username)
        self.assertEqual(formatted_uname,
                         self.user.profile.phone)
        self.assertEqual(1, send_sms.call_count)

    @patch('accounts.views.send_auth_sms')
    def test_sms_truncates_str(self, send_sms):
        url = reverse('accounts.user_by_phone')
        good_uname = '79259737305'
        bad_uname = 'abc{}abc'.format(good_uname)
        payload = {
            'phone': bad_uname,
        }
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)

        self.assertEquals(res.status_code, 200)
        good_uname_plus = '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX,
                                        good_uname)
        users = User.objects.filter(username=good_uname_plus)

        self.assertEquals(len(users), 1)
        self.user = users[0]

        sms_token = SmsToken.objects. \
            filter(user=self.user).last()
        self.assertTrue(sms_token)
        send_sms.assert_called_once_with(self.user)
        self.assertEqual(1, send_sms.call_count)

    @patch('accounts.decoratos.get_google_response')
    @patch('accounts.views.send_auth_sms')
    def test_sms_sent_no_recaptcha_forbidden(self, send_sms, get_google):
        # request with no verify parameter
        get_google.return_value = False
        url = reverse('accounts.user_by_phone')
        uname = '+79259737305'
        payload = {
            'phone': uname,
        }
        self.client.get(self.logout_url)
        res = self.client.post(url, data=payload)

        self.assertEquals(res.status_code, 428)

    @patch('accounts.views.send_auth_sms')
    def test_sms_sent_replace_phone_spaces(self, send_sms):
        self.client.logout()
        url = reverse('accounts.user_by_phone')
        uname = '+49 162 829 04 63'
        expected_uname = '+491628290463'
        payload = {
            'phone': uname,
        }
        res = self.client.post(url, data=payload)
        user = User.objects.last()
        self.assertEquals(res.status_code, 200)

        self.token = SmsToken.objects.\
            filter(user=user).last()

        # test clean-up
        self.assertEqual(expected_uname,
                         user.username)

        send_sms.assert_called_once_with(user)

    @patch('accounts.views.send_auth_sms')
    def test_sms_not_sent_after_limit_is_exceeded(self, send_sms):
        self.client.logout()
        url = reverse('accounts.user_by_phone')
        uname = '+491628290463'
        payload = {
            'phone': uname,
        }
        user = User.objects.last()
        i = 1
        for i in range(1, settings.AXES_LOGIN_FAILURE_LIMIT):
            res = self.client.post(url, data=payload)
            user = User.objects.last()
            self.assertEquals(res.status_code, 200)

            self.token = SmsToken.objects.\
                filter(user=user).last()
            self.assertEquals(send_sms.call_count, i)

        res = self.client.post(url, data=payload)
        newest_user = User.objects.last()
        self.assertEqual(user, newest_user)
        self.assertEquals(res.status_code, 403)
        self.assertEquals(send_sms.call_count, i + 1)

    @patch('accounts.views.send_auth_sms')
    def test_sms_sent_after_limit_is_exceeded_and_time_passed(self, send_sms):
        self.client.logout()
        url = reverse('accounts.user_by_phone')
        uname = '+491628290463'
        payload = {
            'phone': uname,
        }
        user = User.objects.last()
        i = 1
        for i in range(1, settings.AXES_LOGIN_FAILURE_LIMIT):
            res = self.client.post(url, data=payload)
            user = User.objects.last()
            self.assertEquals(res.status_code, 200)

            self.token = SmsToken.objects. \
                filter(user=user).last()

        res = self.client.post(url, data=payload)
        newest_user = User.objects.last()
        self.assertEquals(send_sms.call_count, i + 1)
        self.assertEqual(user, newest_user)
        self.assertEquals(res.status_code, 403)

        unlock_time = datetime.now() +\
            settings.AXES_COOLOFF_TIME

        with freeze_time(unlock_time, tick=True):
            res = self.client.post(url, data=payload)
            user = User.objects.last()
            self.assertEquals(res.status_code, 200)

            self.token = SmsToken.objects. \
                filter(user=user).last()

            # test cleanupm
            self.assertEqual(uname,
                             user.username)

            self.assertEquals(send_sms.call_count, i + 2)

    def test_sms_sent_invalid_phone(self):
        self.client.logout()
        url = reverse('accounts.user_by_phone')
        uname = '+7 92 59 73 73zaza'
        payload = {
            'phone': uname,
        }
        res = self.client.post(url, data=payload)

        self.assertEquals(res.status_code, 400)

        self.user = User.objects.last()
        self.token = SmsToken.objects.last()

    def test_block_after_x_attempts(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = '{}xx'.format(sms_token.sms_token)

        for i in range(1, settings.AXES_LOGIN_FAILURE_LIMIT):
            response = passive_authentication_helper(
                self.client,
                self.user,
                token,
                self.username,
                False
            )

        response = passive_authentication_helper(
            self.client,
            self.user,
            token,
            self.username,
            False
        )

        self.assertEqual(403, response.status_code)

    def test_unblock_after_lockout_passed(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = '{}xx'.format(sms_token.sms_token)

        for i in range(0, settings.AXES_LOGIN_FAILURE_LIMIT):
            response = passive_authentication_helper(
                self.client,
                self.user,
                token,
                self.username,
                False
            )

        unlock_time = datetime.now() + \
            settings.AXES_COOLOFF_TIME + timedelta(seconds=5)

        with freeze_time(unlock_time, tick=True):
            sms_token = SmsToken(user=user)
            sms_token.save()
            token = '{}'.format(sms_token.sms_token)

            response = passive_authentication_helper(
                self.client,
                self.user,
                token,
                self.username,
                False
            )

            self.assertEqual(201, response.status_code)

    def test_correct_token_after_expiry_failure(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = '{}'.format(sms_token.sms_token)

        expiry_time = datetime.now() + settings.SMS_TOKEN_VALIDITY
        with freeze_time(expiry_time):
            response = passive_authentication_helper(
                self.client,
                self.user,
                token,
                self.username,
                False
            )

            self.assertEqual(410, response.status_code)
