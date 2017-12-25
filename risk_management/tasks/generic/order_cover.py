from risk_management.models import Cover
from orders.models import Order
from .currency_cover import CurrencyCover


class OrderCover(CurrencyCover):

    def run(self, order_id):
        cover = amount_to_send = send_to_main = False
        order = Order.objects.get(pk=order_id)
        if order.pair.base.code in self.ALLOWED_COINS:
            currency = order.pair.base
            amount = order.amount_base
        elif order.pair.quote.code in self.ALLOWED_COINS:
            currency = order.pair.quote
            amount = - order.amount_quote
        else:
            self.logger.info(
                'Do not create Cover. Order {} base and quote is not in '
                'ALLOWED_CURRENCIES'.format(
                    order.unique_reference
                )
            )
            return cover, send_to_main, amount_to_send
        reserve = currency.reserve_set.get()
        self.update_reserve_accounts_balances(reserve)
        if Cover.objects.filter(orders=order_id):
            self.logger.info(
                'Do not create Cover. Order {} already has a Cover'.format(
                    order.unique_reference
                )
            )
            return cover, send_to_main, amount_to_send
        cover = super(OrderCover, self).run(currency.code, amount)
        if cover:
            cover.orders.add(order)
            if not order.coverable and cover.cover_type == Cover.BUY:
                amount_to_send = cover.amount_to_main_account
                send_to_main = True

            return cover, send_to_main, amount_to_send
