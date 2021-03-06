from core.tests.base import UserBaseTestCase
from verification.models import Verification, VerificationCategory
from payments.models import PaymentPreference
from django.urls import reverse


class VerificationTestCase(UserBaseTestCase):
    fixtures = [
        'currency_fiat.json',
        'payment_method.json',
        'tier0.json',
        'tier1.json',
        'tier2.json',
        'tier3.json'
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

    def test_check_name(self):
        full_name = 'First Middle Last'
        ver = Verification.objects.create(full_name=full_name)
        ok_name_list = [
            full_name,
            full_name.upper(),
            full_name.lower(),
            ' ' + full_name,
            full_name + ' ',
            'First Last',
            'F. M. Last',
            'F M Last'
        ]
        bad_name_list = [
            'First Middle SecondMiddle Last',
            '',
            None,
            'Smth different',
            'First Biddle Last'
        ]
        for name in ok_name_list:
            self.assertTrue(
                ver.check_name(name), '"{}" != "{}", should be =='.format(
                    full_name, name
                )
            )
        for name in bad_name_list:
            self.assertFalse(
                ver.check_name(name), '"{}" == "{}", should be !='.format(
                    full_name, name
                )
            )

    def test_flaggable_category(self):
        c_flag = VerificationCategory.objects.create(
            name='Badumts Flag', flagable=True
        )
        c_normal = VerificationCategory.objects.create(
            name='Badumts', flagable=False
        )
        kyc = Verification.objects.create()
        self.assertFalse(kyc.flagged)
        kyc.category.add(c_normal)
        kyc.refresh_from_db()
        self.assertFalse(kyc.flagged)
        kyc.category.add(c_flag)
        kyc.refresh_from_db()
        self.assertTrue(kyc.flagged)
        # Assure that signal is not called when category is not add
        kyc.flagged = False
        kyc.save()
        self.assertFalse(kyc.flagged)
        kyc.refresh_from_db()

    def test_demo(self):
        url = reverse('verification.idenfy_callback')
        self.client.post(url, {'asd':'asd'}, format='json')
