from .uphold import UpholdApiClient
from .rpc import ScryptRpcApiClient


class ApiClientFactory:
    UPHOLD = UpholdApiClient()
    SCRYPT = ScryptRpcApiClient()

    @classmethod
    def get_api_client(cls, node):
        if node in cls.UPHOLD.related_nodes:
            return cls.UPHOLD
        elif node in cls.SCRYPT.related_nodes:
            return cls.SCRYPT
