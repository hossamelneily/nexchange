from nexchange.api_clients.rpc import ScryptRpcApiClient, EthashRpcApiClient,\
    Blake2RpcApiClient, ZcashRpcApiClient


scrypt_client = ScryptRpcApiClient()
ethash_client = EthashRpcApiClient()
blake2_client = Blake2RpcApiClient()
zcash_client = ZcashRpcApiClient()

assert \
    scrypt_client.related_nodes[0] \
    != scrypt_client.related_nodes[1] \
    != scrypt_client.related_nodes[2] \
    != scrypt_client.related_nodes[3] \
    != scrypt_client.related_nodes[4] \
    != zcash_client.related_nodes[0] \
    != ethash_client.related_nodes[0] \
    != blake2_client.related_nodes[0]
clients_lookup = {
    scrypt_client.related_nodes[0]: scrypt_client,
    scrypt_client.related_nodes[1]: scrypt_client,
    scrypt_client.related_nodes[2]: scrypt_client,
    scrypt_client.related_nodes[3]: scrypt_client,
    scrypt_client.related_nodes[4]: scrypt_client,
    zcash_client.related_nodes[0]: zcash_client,
    ethash_client.related_nodes[0]: ethash_client,
    blake2_client.related_nodes[0]: blake2_client,
}


def create_deposit_address(user, order):
    currency = order.pair.quote
    card, address = clients_lookup[
        currency.wallet].create_user_wallet(user, currency)
    order.deposit_address = address
    order.save()
