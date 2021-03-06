from nexchange.rpc.scrypt import ScryptRpcApiClient
from nexchange.rpc.ethash import EthashRpcApiClient
from nexchange.rpc.blake2 import Blake2RpcApiClient
from nexchange.rpc.zcash import ZcashRpcApiClient
from nexchange.rpc.omni import OmniRpcApiClient
from nexchange.rpc.cryptonight import CryptonightRpcApiClient
from nexchange.rpc.ripple import RippleRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient
from orders.models import Order
from decimal import Decimal


class UpholdBackendMixin:

    def __init__(self):
        self.api = UpholdApiClient()
        super(UpholdBackendMixin, self).__init__()

    def update_unconfirmed_order(self, order, tx_data):
        if any(['tx_id_api' not in tx_data,
                order.status != Order.PAID_UNCONFIRMED,
                order.amount_quote != Decimal(str(tx_data['amount']))]):
            self.logger.info(
                'Cannot update Unconfirmed order :{} with this transaction '
                'data:{}'.format(order, tx_data))
            return
        filters = {k: v for k, v in tx_data.items() if v}
        filters['tx_id_api'] = None
        tx = order.transactions.filter(**filters).last()
        if tx:
            tx.tx_id_api = tx_data.get('tx_id_api')
            tx.save()


class ScryptRpcMixin:

    def __init__(self):
        self.api = ScryptRpcApiClient()
        super(ScryptRpcMixin, self).__init__()


class ZcashRpcMixin:

    def __init__(self):
        self.api = ZcashRpcApiClient()
        super(ZcashRpcMixin, self).__init__()


class OmniRpcMixin:

    def __init__(self):
        self.api = OmniRpcApiClient()
        super(OmniRpcMixin, self).__init__()


class EthashRpcMixin:

    def __init__(self):
        self.api = EthashRpcApiClient()
        super(EthashRpcMixin, self).__init__()


class Blake2RpcMixin:

    def __init__(self):
        self.api = Blake2RpcApiClient()
        super(Blake2RpcMixin, self).__init__()


class CryptonightRpcMixin:

    def __init__(self):
        self.api = CryptonightRpcApiClient()
        super(CryptonightRpcMixin, self).__init__()


class RippleRpcMixin:

    def __init__(self):
        self.api = RippleRpcApiClient()
        super(RippleRpcMixin, self).__init__()
