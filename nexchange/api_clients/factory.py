from .uphold import UpholdApiClient
from .rpc import ScryptRpcApiClient


class ApiClientFactory:
    UPHOLD = UpholdApiClient()
    DOGE = ScryptRpcApiClient()

    @classmethod
    def get_api_client(cls, node):
        if node == 'api1':
            return cls.UPHOLD
        elif node == 'rpc2':
            return cls.DOGE
