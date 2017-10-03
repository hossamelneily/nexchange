from nexchange.api_clients.rpc import ScryptRpcApiClient
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
