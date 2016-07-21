from django.test import TestCase
from core.models import PaymentPreference


class TestPaymentPreference(TestCase):
    def test_bin_guessing_fixtures(self):
        preferences = PaymentPreference.objects.all()
        for pref in preferences:
            self.assertEqual(pref.guess_payment_method(), pref.payment_method)

    def test_bin_guessing_provider(self):
        pass

    def test_guess_bin_on_save(self):
        pass
