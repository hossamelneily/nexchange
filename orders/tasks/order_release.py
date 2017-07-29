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
        exchange=False,
        flagged=False
    )

    for order in orders[::-1]:
        order.refresh_from_db()
        if order.status not in Order.IN_RELEASED:
            send_money_status = utils.send_money(order.pk)
            if send_money_status:
                order.status = Order.COMPLETED
                order.save()
                logger.info('Order {} is released, client paid'.format(order))
                order.notify()
            else:
                msg = 'Order {} cannot be paid automatically.'.format(order)
                order.flag(val=msg)
                raise NotImplementedError(msg)
        else:
            msg = 'Order {} already released'.format(order)
            logger.error(msg)
            return False
