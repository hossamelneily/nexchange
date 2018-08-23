from __future__ import absolute_import
from django.conf import settings
from nexchange.rpc.scrypt import ScryptRpcApiClient
from nexchange.rpc.ethash import EthashRpcApiClient
from nexchange.rpc.blake2 import Blake2RpcApiClient
from nexchange.rpc.zcash import ZcashRpcApiClient
from nexchange.rpc.omni import OmniRpcApiClient

scrypt_client = ScryptRpcApiClient()
zcash_client = ZcashRpcApiClient()
omni_client = OmniRpcApiClient()
ethash_client = EthashRpcApiClient()
blake2_client = Blake2RpcApiClient()
clients = [scrypt_client, zcash_client, ethash_client, blake2_client,
           omni_client]


def renew_cards_reserve(expected_reserve=settings.CARDS_RESERVE_COUNT):
    for client in clients:
        try:
            client.renew_cards_reserve(expected_reserve=expected_reserve)
        except Exception as e:
            client.logger.error('Cannot renew cards reserve. Error: {}'.format(
                e))
