from core.tests.base import UserBaseTestCase
from verification.models import Verification
from payments.models import PaymentPreference


class VerificationTestCase(UserBaseTestCase):
    fixtures = [
        'currency_fiat.json',
        'payment_method.json',
        'tier0.json',
        'tier1.json'
    ]

    def setUp(self):
        super().setUp()
        self.verification_data = {
            'user': self.user,
        }

    def test_create_verification(self):
        verification = Verification(**self.verification_data)
        verification.save()

    def test_get_file_name_without_provider_system_id(self):
        verification = Verification()
        verification.save()
        path1 = verification._get_file_name('name', 'root')
        pref = PaymentPreference(payment_method_id=1)
        pref.save()
        self.assertIsNone(pref.provider_system_id)
        verification.payment_preference = pref
        verification.save()
        path2 = verification._get_file_name('name', 'root')
        self.assertTrue(isinstance(path2, str))
        self.assertEqual(path1, path2)

    def test_get_file_name_remove_special_characters(self):
        verification = Verification()
        verification.save()
        pref = PaymentPreference(payment_method_id=1,
                                 provider_system_id='/a=b}c')
        pref.save()
        verification.payment_preference = pref
        verification.save()
        path = verification._get_file_name('name', 'root')
        self.assertIn('abc', path)
