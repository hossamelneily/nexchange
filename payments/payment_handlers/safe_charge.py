from payments.api_clients.safe_charge import SafeChargeAPIClient
from .base import BasePaymentHandler


class SafeChargePaymentHandler(SafeChargeAPIClient, BasePaymentHandler):
    def __init__(self):
        BasePaymentHandler.__init__(self)
        SafeChargeAPIClient.__init__(self)
