from .generic.ok_pay import OkPayPaymentChecker  # noqa
from .generic.payeer import PayeerPaymentChecker  # noqa


def run_payer():
    payeer_importer = PayeerPaymentChecker()
    payeer_importer.run()


def run_okpay():
    ok_pay_importer = OkPayPaymentChecker()
    ok_pay_importer.run()
