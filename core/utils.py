from nexchange.api_clients.rpc import ScryptRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient

scrypt_client = ScryptRpcApiClient()
uphold_client = UpholdApiClient()

assert scrypt_client.related_nodes[0] \
    != scrypt_client.related_nodes[1] \
    != scrypt_client.related_nodes[2] \
    != uphold_client.related_nodes[0]

clients_lookup = {
    scrypt_client.related_nodes[0]: scrypt_client,
    scrypt_client.related_nodes[1]: scrypt_client,
    scrypt_client.related_nodes[2]: scrypt_client,
    uphold_client.related_nodes[0]: uphold_client
}


def create_deposit_address(user, order):
    currency = order.pair.quote
    card, address = clients_lookup[
        currency.wallet].create_user_wallet(user, currency)
    order.deposit_address = address
    order.save()
