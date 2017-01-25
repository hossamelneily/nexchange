from __future__ import absolute_import
from .generic.ok_pay import OkPayPaymentChecker
from .generic.payeer import PayeerPaymentChecker

import_payeer_payments = PayeerPaymentChecker()
import_okpay_payments = OkPayPaymentChecker()
