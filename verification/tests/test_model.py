from django.db.utils import IntegrityError

from core.tests.base import UserBaseTestCase
from verification.models import Verification


class VerificationTestCase(UserBaseTestCase):

    def setUp(self):
        super().setUp()
        self.verification_data = {
            'user': self.user,
        }

    def test_create_verification(self):
        verification = Verification(**self.verification_data)
        verification.save()

    def test_create_verification_without_user(self):
        verification = Verification()
        with self.assertRaises(IntegrityError):
            verification.save()
