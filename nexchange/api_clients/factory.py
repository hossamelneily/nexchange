from .uphold import UpholdApiClient
from nexchange.rpc.scrypt import ScryptRpcApiClient
from nexchange.rpc.ethash import EthashRpcApiClient
from nexchange.rpc.blake2 import Blake2RpcApiClient
from nexchange.rpc.zcash import ZcashRpcApiClient
from nexchange.rpc.omni import OmniRpcApiClient
from nexchange.rpc.cryptonight import CryptonightRpcApiClient
from nexchange.rpc.ripple import RippleRpcApiClient
from .bittrex import BittrexApiClient
from .kraken import KrakenApiClient


class ApiClientFactory:
    UPHOLD = UpholdApiClient()
    SCRYPT = ScryptRpcApiClient()
    ETHASH = EthashRpcApiClient()
    BITTREX = BittrexApiClient()
    KRAKEN = KrakenApiClient()
    BLAKE2 = Blake2RpcApiClient()
    ZCASH = ZcashRpcApiClient()
    OMNI = OmniRpcApiClient()
    CRYPTONIGHT = CryptonightRpcApiClient()
    RIPPLE = RippleRpcApiClient()

    @classmethod
    def get_api_client(cls, node):
        if node in cls.UPHOLD.related_nodes:
            return cls.UPHOLD
        elif node in cls.SCRYPT.related_nodes:
            return cls.SCRYPT
        elif node in cls.BITTREX.related_nodes:
            return cls.BITTREX
        elif node in cls.KRAKEN.related_nodes:
            return cls.KRAKEN
        elif node in cls.ETHASH.related_nodes:
            return cls.ETHASH
        elif node in cls.BLAKE2.related_nodes:
            return cls.BLAKE2
        elif node in cls.ZCASH.related_nodes:
            return cls.ZCASH
        elif node in cls.OMNI.related_nodes:
            return cls.OMNI
        elif node in cls.CRYPTONIGHT.related_nodes:
            return cls.CRYPTONIGHT
        elif node in cls.RIPPLE.related_nodes:
            return cls.RIPPLE
