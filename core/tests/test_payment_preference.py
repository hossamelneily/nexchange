from django.test import TestCase
from core.models import PaymentPreference, PaymentMethod
from core.models import User


class TestPaymentPreference(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.user, created = \
            User.objects.get_or_create(username='onit')
        super(TestPaymentPreference, cls).setUpClass()

    def test_bin_guessing_fixtures(self):
        preferences = PaymentPreference.objects.all()
        for pref in preferences:
            self.assertEqual(pref.guess_payment_method(), pref.payment_method)

    def test_bin_guessing_provider(self):
        # TODO: w00t?
        pass

    def test_guess_bin_on_save(self):
        test_bin = "123"
        suffix = "321"
        pm = PaymentMethod(bin=test_bin)
        pm.save()

        identifier = "{}{}".format(test_bin, suffix)
        p = PaymentPreference(identifier=identifier, user=self.user)
        p.save()
        self.assertEqual(p.payment_method, pm)

    def test_longest_match_first(self):
        test_bin_one = "123"
        test_bin_two = "1"
        suffix = "321"

        identifier = "{}{}".format(test_bin_one, suffix)

        pm_one = PaymentMethod(bin=test_bin_one)
        pm_one.save()

        pm_two = PaymentMethod(bin=test_bin_two)
        pm_two.save()

        pp = PaymentPreference(user=self.user, identifier=identifier)
        pp.save()

        self.assertEqual(pm_one, pp.payment_method)
        self.assertIn(test_bin_two, test_bin_one)
