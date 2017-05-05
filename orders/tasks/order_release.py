from __future__ import absolute_import
from orders.models import Order
from nexchange.utils import get_nexchange_logger
from orders import utils


def sell_order_release():
    logger = get_nexchange_logger(__name__)
    orders = Order.objects.filter(
        status=Order.PAID,
        order_type=Order.SELL,
        transactions__isnull=False,
        exchange=False
    )

    for order in orders[::-1]:
        send_money_status = utils.send_money(order.pk)
        if send_money_status:
            order.status = Order.COMPLETED
            order.save()
            logger.info('Order {} is released, client paid'.format(order))
        else:
            raise NotImplementedError(
                'Order {} cannot be paid automatically.'.format(order)
            )
