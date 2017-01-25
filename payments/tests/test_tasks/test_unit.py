from unittest import TestCase
from payments.tasks.schedule.generic.base import BasePaymentChecker  # noqa
from unittest.mock import patch
from core.tests.utils import data_provider
from payments.tasks.schedule.generic.ok_pay import OkPayPaymentChecker  # noqa
from payments.tasks.schedule.generic.payeer import PayeerAPIClient  # noqa


class BasePaymentCheckerTestCase(TestCase):
    ABSTRACT_METHODS = [
        'transactions_iterator',
        'get_transactions',
    ]

    def __init__(self, *args, **kwargs):
        self.checker = None
        super(BasePaymentCheckerTestCase, self)\
            .__init__(*args, **kwargs)

    @staticmethod
    def get_data_set(data_set):
        return lambda: ((data_item,)
                        for data_item in data_set)

    # trivial stuff
    @patch('payments.models.PaymentMethod.objects.get')
    @patch('payments.models.PaymentPreference.objects.get')
    def test_init_logic(self, get_payment, get_pref):
        self.checker = BasePaymentChecker()
        payment_pref = '__pref__'
        payment_method = '__payment__'
        get_payment.return_value = payment_pref
        get_pref.return_value = payment_method
        self.assertIsInstance(self.checker.currency_cache, dict)
        self.assertIsInstance(self.checker.transactions, list)
        self.assertTrue(hasattr(self.checker, 'api'))
        self.assertTrue(hasattr(self.checker, 'payment_preference'))
        self.assertIsInstance(self.checker.required_data_keys, list)

    @data_provider(get_data_set.__func__(ABSTRACT_METHODS))
    @patch('payments.models.PaymentMethod.objects.get')
    @patch('payments.models.PaymentPreference.objects.get')
    def test_abstract_methods_throw_exception(self, abc_method,
                                              method, preference):
        self.checker = BasePaymentChecker()
        try:
            getattr(self.checker, abc_method)()
            self.assertTrue(False)
        except NotImplementedError:
            self.assertTrue(True)

    # some unit tests
    def test_run(self):
        pass

    def test_get_currency_db(self):
        pass

    def test_get_currency_cache(self):
        pass

    def test_parse_data(self):
        pass

    def test_validate_payment_success(self):
        pass

    def test_validate_payment_fail_status(self):
        pass

    def test_validate_payment_fail_beneficiary(self):
        pass

    def test_create_payment_new(self):
        pass

    def test_create_payment_exists(self):
        pass

    def test_create_payment_preference_new(self):
        pass

    def test_create_payment_preference_exists_match_by_primary(self):
        pass

    def test_create_payment_preference_exists_match_by_secondary(self):
        pass

    def test_create_payment_preference_exists_duplicate(self):
        # same as match by both
        pass


class PayeerPaymentChecker(TestCase):

    def test_init_logic(self):
        pass

    def test_get_transactions(self):
        pass

    def test_validate_success_ok(self):
        pass

    def test_validate_success_fail(self):
        pass

    def test_validate_beneficiary_ok(self):
        pass

    def test_validate_beneficiary_fail(self):
        pass

    def test_parse_data_extract_email_from_regex(self):
        pass

    def test_parse_data_extract_wallet_from_regex(self):
        pass

    def test_parse_data_extract_wallet_from_res(self):
        pass

    def test_parse_data_ignore_res_wallet_from_if_placeholder(self):
        # ignore wallet if the value is placeholder
        pass

    def test_parse_data_ignore_res_wallet_from_if_exists(self):
        # ignore wallet if found by regex
        pass


class OkPayPaymentCheckerTestCase(TestCase):

    def test_init_logic(self):
        pass

    def test_get_transactions(self):
        pass

    def test_validate_success_ok(self):
        pass

    def test_validate_success_fail(self):
        pass

    def test_validate_beneficiary_ok(self):
        pass

    def test_validate_beneficiary_fail(self):
        pass
