from __future__ import absolute_import
from django.conf import settings
from nexchange.api_clients.rpc import ScryptRpcApiClient, EthashRpcApiClient,\
    Blake2RpcApiClient, ZcashRpcApiClient

scrypt_client = ScryptRpcApiClient()
zcash_client = ZcashRpcApiClient()
ethash_client = EthashRpcApiClient()
blake2_client = Blake2RpcApiClient()
clients = [scrypt_client, zcash_client, ethash_client, blake2_client]


def renew_cards_reserve(expected_reserve=settings.CARDS_RESERVE_COUNT):
    for client in clients:
        try:
            client.renew_cards_reserve(expected_reserve=expected_reserve)
        except Exception as e:
            client.logger.error('Cannot renew cards reserve. Error: {}'.format(
                e))
