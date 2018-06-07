from nexchange.rpc.scrypt import ScryptRpcApiClient
from nexchange.rpc.ethash import EthashRpcApiClient
from nexchange.rpc.blake2 import Blake2RpcApiClient
from nexchange.rpc.zcash import ZcashRpcApiClient
from nexchange.rpc.omni import OmniRpcApiClient
from nexchange.rpc.cryptonight import CryptonightRpcApiClient

scrypt_client = ScryptRpcApiClient()
ethash_client = EthashRpcApiClient()
blake2_client = Blake2RpcApiClient()
zcash_client = ZcashRpcApiClient()
omni_client = OmniRpcApiClient()
cryptonight_client = CryptonightRpcApiClient()

assert \
    scrypt_client.related_nodes[0] \
    != scrypt_client.related_nodes[1] \
    != scrypt_client.related_nodes[2] \
    != scrypt_client.related_nodes[3] \
    != scrypt_client.related_nodes[4] \
    != zcash_client.related_nodes[0] \
    != omni_client.related_nodes[0] \
    != ethash_client.related_nodes[0] \
    != blake2_client.related_nodes[0] \
    != cryptonight_client.related_nodes[0]

clients_lookup = {
    scrypt_client.related_nodes[0]: scrypt_client,
    scrypt_client.related_nodes[1]: scrypt_client,
    scrypt_client.related_nodes[2]: scrypt_client,
    scrypt_client.related_nodes[3]: scrypt_client,
    scrypt_client.related_nodes[4]: scrypt_client,
    zcash_client.related_nodes[0]: zcash_client,
    omni_client.related_nodes[0]: omni_client,
    ethash_client.related_nodes[0]: ethash_client,
    blake2_client.related_nodes[0]: blake2_client,
    cryptonight_client.related_nodes[0]: cryptonight_client,
}


def create_deposit_address(user, order):
    currency = order.pair.quote
    card, address = clients_lookup[
        currency.wallet].create_user_wallet(user, currency)
    order.deposit_address = address
    order.save()
