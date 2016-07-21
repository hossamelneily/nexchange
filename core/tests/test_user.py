from django.test import TestCase
from core.models import SmsToken, Profile
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from .utils import UserBaseTestCase


class RegistrationTestCase(TestCase):

    def setUp(self):
        self.data = {
            'phone': '+555190909891',
            'password1': '123Mudar',
            'password2': '123Mudar',
        }
        super(RegistrationTestCase, self).setUp()

    def test_can_register(self):
        response = self.client.post(
            reverse('core.user_registration'), self.data)

        # Redirect is to user profile Page
        self.assertEqual(302, response.status_code)
        self.assertEqual(reverse('core.user_profile'), response.url)

        # Saved data Ok
        user = User.objects.last()
        self.assertEqual(self.data['phone'], user.profile.phone)

    def test_cannot_register_existant_phone(self):

        # Creates first with the phone
        self.client.post(
            reverse('core.user_registration'),
            self.data
        )

        # ensure is created
        self.assertIsInstance(
            Profile.objects.get(phone=self.data['phone']), Profile)

        response = self.client.post(
            reverse('core.user_registration'), self.data)

        self.assertFormError(response, 'profile_form', 'phone',
                             'This phone is already registered.')


class ProfileUpdateTestCase(UserBaseTestCase):
    def test_can_update_profile(self):
        response = self.client.post(reverse('core.user_profile'), self.data)
        # Redirect after update
        self.assertEqual(302, response.status_code)

        # saved the User instance data
        user = User.objects.get(email=self.data['email'])
        self.assertEqual(user.profile.first_name, self.data[
                         'first_name'])  # saved the profile too
        self.assertEqual(user.profile.last_name, self.data['last_name'])

    def test_phone_verification_with_success(self):
        user = self.user
        # Ensure profile is disabled
        profile = user.profile
        profile.disabled = True
        profile.save()
        self.assertTrue(user.profile.disabled)
        sms_token = SmsToken.objects.filter(user=user).latest('id')
        token = sms_token.sms_token

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})

        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        self.assertJSONEqual(
            '{"status": "OK"}',
            str(response.content, encoding='utf8'))

        # Ensure profile was enabled
        self.assertFalse(user.profile.disabled)

    def test_phone_verification_fails_with_wrong_token(self):
        # incorrect token
        token = "{}XX".format(SmsToken.get_sms_token())

        response = self.client.post(
            reverse('core.verify_phone'), {'token': token})
        # Ensure the token was correctly received
        self.assertEqual(200, response.status_code)
        self.assertJSONEqual('{"status": "NO_MATCH"}',
                             str(response.content, encoding='utf8'),)


class ShortRegistrationTestCase(TestCase):
    def test_short_registration_success(self):
        pass

    def test_short_registration_failure(self):
        pass