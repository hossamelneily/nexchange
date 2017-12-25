from payments.api_clients.safe_charge import SafeChargeAPIClient


class SafeChargeBackendMixin:

    def __init__(self):
        self.api = SafeChargeAPIClient()
        super(SafeChargeBackendMixin, self).__init__()
