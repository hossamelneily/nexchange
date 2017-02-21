from __future__ import absolute_import
from orders.models import Order
from nexchange.utils import get_nexchange_logger
from django.conf import settings
from orders import utils


def sell_order_release():
    def _check_confirmations(_order, _logger):
        res = True
        for tx in _order.transactions.all():
            if tx.confirmations < tx.address_to.currency.min_confirmations:
                _logger.info('Order {} has unconfirmed transactions'.format(
                    _order)
                )
                res = False
                continue
        return res
    logger = get_nexchange_logger(__name__)
    orders = Order.objects.filter(
        status=Order.PAID_UNCONFIRMED,
        order_type=Order.SELL,
        transactions__isnull=False
    )
    for order in orders[::-1]:
        if not _check_confirmations(order, logger):
            continue
        send_money_status = utils.send_money(order.pk)
        if send_money_status:
            order.status = Order.RELEASED
            order.save()
            logger.info('Order {} is scheduled of released'.format(order))
        else:
            raise NotImplementedError(
                'Order {} cannot be paid automatically.'.format(order)
            )


def exchange_order_release():
    # TODO:
    # This the task to release COINS for clients that
    # EXCHANGE crypto-currencies, I.E. ETH to BTC
    # 1. Auto release funds when coins are credited
    # 2. Move funds from user card to our card
    # 3. Notify admin if auto payment is not available
    # for the payment preference that the user has selected.
    pass
