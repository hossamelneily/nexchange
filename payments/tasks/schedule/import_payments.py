from __future__ import absolute_import
from .generic.ok_pay import OkPayPaymentChecker
from .generic.payeer import PayeerPaymentChecker

payeer = PayeerPaymentChecker()
ok_pay = OkPayPaymentChecker()
