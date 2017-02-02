from __future__ import absolute_import
from core.models import Address, Transaction
from payments.models import Payment
from orders.models import Order
from nexchange.utils import validate_payment_matches_order, \
    release_payment, send_email, send_sms, get_nexchange_logger
from django.utils.translation import activate
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
import logging


def buy_order_release():
    logger = get_nexchange_logger(__name__, True, True)

    for p in Payment.objects.filter(is_success=True,
                                    is_redeemed=False):
        verbose_match = False
        try:
            o = Order.objects.get(is_released=False,
                                  unique_reference=p.reference)
            if o.payment_preference.payment_method !=\
                    p.payment_preference.payment_method:
                # MHM... Odd
                o.moderator_flag = p.pk
                o.save()
                p.moderator_flag = o.pk
                p.save()
                logger.error('Payment: {} Order: {} match exists'
                             'but payment methods do not correspond '
                             'Flagged for moderation - IGNORING'
                             .format(o, p))
                continue

            if not p.user or not p.payment_preference.user:
                user = o.user
                profile = user.profile
                with transaction.atomic(using='default'):
                    p.user = user
                    p.payment_preference.user = user
                    p.save()
                    p.payment_preference.save()
            elif p.user != o.user:
                logger.error('payment {} user {} users don\'t match '
                             'is it a new user with old preference?'
                             .format(p, o))
                continue

            if not o.withdraw_address:
                logging.info('{} has now withdrawal address, moving on'.
                             format(o.unique_reference))
                continue

            logging.info(
                'Found order {} with payment {} '.
                format(o.unique_reference, p)
            )
        except Order.DoesNotExist:
                # Auto order payment
                # or user forgot reference
                # or uses out payout
                # feature
            try:
                pm = p.payment_preference.payment_method
                if p.user and p.payment_preference:
                    o = Order.objects.get(
                        user=p.user,
                        amount_cash=p.amount_cash,
                        payment_preference__payment_method=pm,
                        is_completed=False,
                        currency=p.currency,
                    )
                    user = o.user
                    profile = user.profile
                    verbose_match = True
                else:
                    logger.warn('could not associate payment {}'
                                ' with an order. owner user of wallet '
                                '{} not found. '
                                'SmartMatching disabled.'.format(p, pm))
                    p.moderator_flag = True
                    p.save()
                    continue
            except Order.DoesNotExist:
                logger.error('order for payment {} not found'
                             ' through ID or SmartMatching'.format(p))
                continue

        if validate_payment_matches_order(o, p, verbose_match, logger):
            logging.info('Order {}  VALID {}'
                         .format(o, o.withdraw_address))

            with transaction.atomic(using='default'):
                p.is_complete = True
                p.save()
                tx_id = release_payment(o.withdraw_address,
                                        o.amount_btc)

                if tx_id is None:
                    logging.error('Payment release returned None, '
                                  'order {} payment {}'.format(o, p))
                    continue

                logging.info(
                    'RELEASED order: {} with payment {} '
                    'released tx id: {}'.format(
                        o, p, tx_id
                    )
                )

                o.is_released = True
                o.save()

                p.is_redeemed = True
                p.save()

                # double check
                adr = Address.objects.get(
                    user=o.user,
                    address=o.withdraw_address.address
                )

                t = Transaction(tx_id_api=tx_id, order=o, address_to=adr)
                t.save()

            title = _(
                'Nexchange: Order {} released'.format(
                    o.unique_reference))
            msg = _('Your order {}: is released. Withdraw address: {}')\
                .format(
                o.unique_reference,
                o.withdraw_address
            )

            logging.info('release message sent to client, title: {} | msg: {}'
                         .format(title, msg))

            # Activate translation
            if any([profile.notify_by_email, profile.notify_by_phone]):
                activate(user.profile.lang)

            # send sms depending on notification settings in profile
            if profile.notify_by_phone:
                phone_to = str(o.user.username)
                sms_result = send_sms(msg, phone_to)
                logging.info('sms res: {}'.format(str(sms_result)))

            # send email
            if profile.notify_by_email:
                send_email(user.email, title, msg)


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
