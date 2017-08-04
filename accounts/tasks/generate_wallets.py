from __future__ import absolute_import
from django.conf import settings
from nexchange.api_clients.rpc import ScryptRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient

scrypt_client = ScryptRpcApiClient()
uphold_client = UpholdApiClient()
clients = [scrypt_client, uphold_client]


def renew_cards_reserve(expected_reserve=settings.CARDS_RESERVE_COUNT):
    for client in clients:
        try:
            client.renew_cards_reserve(expected_reserve=expected_reserve)
        except Exception as e:
            client.logger.error('Cannot renew cards reserve. Error: {}'.format(
                e))
