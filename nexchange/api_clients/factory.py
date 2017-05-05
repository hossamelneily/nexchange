from .uphold import UpholdApiClient
from .rpc import ScryptRpcApiClient


class ApiClientFactory:
    UPHOLD = UpholdApiClient()
    RENOS = ScryptRpcApiClient()

    @classmethod
    def get_api_client(cls, node):
        if node == 'api1':
            return cls.UPHOLD
        elif node == 'rpc1':
            return cls.RENOS
