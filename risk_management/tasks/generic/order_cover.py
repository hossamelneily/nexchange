from risk_management.models import Cover
from orders.models import Order
from .currency_cover import CurrencyCover


class OrderCover(CurrencyCover):

    def run(self, order_id):
        order = Order.objects.get(pk=order_id)
        currency = order.pair.base
        reserve = currency.reserve_set.get()
        self.update_reserve_accounts_balances(reserve)
        if order.coverable:
            self.logger.info(
                'Do not create Cover. Order {} is already coverable'.format(
                    order.unique_reference)
            )
            return
        if Cover.objects.filter(orders=order_id):
            self.logger.info(
                'Do not create Cover. Order {} already has a Cover'.format(
                    order.unique_reference
                )
            )
            return
        cover = super(OrderCover, self).run(currency.code, order.amount_base)
        if cover:
            cover.orders.add(order)
            return cover
