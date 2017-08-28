from nexchange.api_clients.rpc import ScryptRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient


class UpholdBackendMixin:

    def __init__(self):
        self.api = UpholdApiClient()
        super(UpholdBackendMixin, self).__init__()


class ScryptRpcMixin:

    def __init__(self):
        self.api = ScryptRpcApiClient()
        super(ScryptRpcMixin, self).__init__()
