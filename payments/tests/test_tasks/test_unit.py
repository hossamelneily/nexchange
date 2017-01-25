from unittest import TestCase
from payments.tasks.schedule.generic.base import BasePaymentChecker  # noqa
from payments.tasks.schedule.generic.ok_pay import OkPayPaymentChecker  # noqa
from payments.tasks.schedule.generic.payeer import PayeerAPIClient  # noqa


class BasePaymentCheckerTestCase(TestCase):

    def test_run(self):
        pass

    # trivial stuff
    def test_init_logic(self):
        pass

    def test_abstract_methods_throw_exception(self):
        pass

    # some unit tests
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
