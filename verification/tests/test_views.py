from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.test import Client
from PIL import Image

from core.tests.base import UserBaseTestCase
from verification.models import Verification
from unittest.mock import patch


class VerificationViewTestCase(UserBaseTestCase):

    def setUp(self):
        super().setUp()

        # create Mockup picture
        image = Image.new('RGBA', size=(50, 50), color=(155, 0, 0))
        image_file = BytesIO(image.tobytes())
        image_file.name = 'test.png'
        image_file.seek(0)
        django_friendly_file = ContentFile(image_file.read(), 'test.png')

        self.verification_data = {
            'user': self.user,
            'identity_document': django_friendly_file,
            'utility_document': django_friendly_file
        }
        self.verification = Verification(**self.verification_data)
        self.verification.save()
        name = self.verification.identity_document.name
        util_name = self.verification.utility_document.name
        self.url = reverse('verification.download', kwargs={'file_name': name})
        self.util_url = reverse('verification.download',
                                kwargs={'file_name': util_name})

        # another client
        username = '+555190909100'
        password = '321Changed'
        User.objects.create_user(username=username, password=password)
        self.client2 = Client()
        self.client2.login(username=username, password=password)

    def test_download_document(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    def test_redirect_download_for_anonymus(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(302, response.status_code)
        success = self.client.login(
            username=self.username, password=self.password)
        self.assertTrue(success)

    def test_forbidden_download_for_different_user(self):
        for url in [self.util_url, self.url]:
            response = self.client2.get(url)
            self.assertEqual(403, response.status_code)
