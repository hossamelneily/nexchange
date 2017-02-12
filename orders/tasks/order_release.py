from __future__ import absolute_import
from core.models import Address, Transaction
from payments.models import Payment
from orders.models import Order
from nexchange.utils import release_payment, send_email, send_sms, get_nexchange_logger
from django.utils.translation import activate
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
import logging


def sell_order_release():
    def _check_confirmations(_order, _logger):
        res = True
        for txs in _order.transactions.all():
            if txs.confirmations < settings.MIN_REQUIRED_CONFIRMATIONS:
                _logger.info('Order {} has unconfirmed transactions'.format(
                    _order)
                )
                res = False
                continue
        return res
    logger = get_nexchange_logger(__name__)
    orders = Order.objects.filter(
        is_paid=True, is_completed=False,
        order_type=Order.SELL, is_released=False,
        transactions__isnull=False
    )
    for order in orders[::-1]:
        if not _check_confirmations(order, logger):
            continue
        status = order.send_money()
        if status:
            # TODO: move this to send money
            order.is_released = True
            order.save()
            logger.info('Order {} is released'.format(order))
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
