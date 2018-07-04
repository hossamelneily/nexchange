from nexchange.tasks.base import BaseTask
from decimal import Decimal
from nexchange.rpc.ethash import EthashRpcApiClient
from ico.models import Subscription
from core.validators import validate_eth
from orders.models import Order
from ticker.models import Price


class BaseIcoManagerTask(BaseTask):

    def __init__(self, *args, **kwargs):
        super(BaseIcoManagerTask, self).__init__(*args, **kwargs)
        self.api = EthashRpcApiClient()

    def _get_subscription(self, subscription_id):
        return Subscription.objects.get(pk=subscription_id)

    def _get_address_str(self, subscription):
        _address = subscription.sending_address
        try:
            validate_eth(_address)
        except ValueError:
            self.logger.warning(
                'Invalid address on subscription {}'.format(subscription.pk)
            )
        return _address

    def _get_address_orders(self, address):
        return Order.objects.filter(
            status__in=[Order.COMPLETED, Order.RELEASED],
            withdraw_address__address__iexact=address
        )

    def _get_total_order_turnover(self, orders, currency='ETH'):
        turnover = Decimal('0')
        for order in orders:
            turnover += Price.convert_amount(order.amount_base,
                                             order.pair.base, currency)
        return turnover

    def set_eth_balance(self, subscription_id):
        sub = self._get_subscription(subscription_id)
        _address = self._get_address_str(sub)
        _balance = self.api.get_balance('ETH', account=_address)
        if isinstance(_balance, Decimal):
            sub.eth_balance = _balance
            sub.save()
        else:
            self.logger.info(
                'Smth wrong with ICO Subscribtion {} balance check'.format(
                    subscription_id
                )
            )

    def set_address_turnover(self, subscription_id):
        sub = self._get_subscription(subscription_id)
        _address = self._get_address_str(sub)
        _orders = self._get_address_orders(_address)
        sub.address_turnover = self._get_total_order_turnover(_orders)
        sub.save()
