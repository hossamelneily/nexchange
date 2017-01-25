from __future__ import absolute_import
from core.models import Address, Transaction
from payments.models import Payment
from orders.models import Order
from nexchange.utils import validate_payment_matches_order, \
    release_payment, send_email, send_sms
from django.utils.translation import activate
from celery import shared_task
from django.utils.translation import ugettext_lazy as _
import logging


@shared_task
def buy_order_release():
    logger = logging.getLogger('buy_order_release')
    # TODO: iterate over payments instead, will be much faster
    for o in Order.objects.filter(is_paid=True,
                                  is_released=False,
                                  order_type=Order.BUY):
        if not o.withdraw_address:
            logging.info('{} has now withdrawal address, moving on'.
                         format(o.unique_reference))
            continue
        user = o.user
        profile = user.profile
        logging.info('Look up order {} '.
                     format(o.unique_reference))

        # Straight forward, unique ref is there
        p = Payment.objects.filter(
            reference=o.unique_reference,
            is_redeemed=False
        )
        if not p:
            # Auto order payment, or user forgot reference, or uses out payout
            # feautre
            p = Payment.objects.filter(user=user,
                                       amount_cash=o.amount_cash,
                                       payment_preference__payment_method=o.
                                       payment_preference.payment_method,
                                       is_redeemed=False,
                                       currency=o.currency,
                                       ).first()

        validate_payment_matches_order(p, o, logger)

        if p:
            logging.info('Order {} withdraw address {}',
                         o, o.withdraw_address)
            p.is_complete = True
            p.save()
            tx_id = release_payment(o.withdraw_address,
                                    o.amount_btc)

            if tx_id is None:
                logging.info('Payment release returned None, '
                             'order {} payment {}'.format(o, p))
                continue

            logging.info('order: {} with payment {} released tx id: {}'
                         .format(o, p, tx_id))
            o.is_released = True
            o.save()

            p.is_redeemed = True
            p.save()

            adr = Address.objects.get(
                user=o.user, address=o.withdraw_address)

            t = Transaction(tx_id_api=tx_id, order=o, address_to=adr)
            t.save()

            title = _('Nexchange: Order released')
            msg = _('Your order {}:  is released').format(o.unique_reference)

            logging.info('release message sent to client, title: {} | msg: {}'
                         .format(title, msg))

            # Activate translation
            if any([profile.notify_by_email, profile.notify_by_phone]):
                activate(user.prile.language)

            # send sms depending on notification settings in profile
            if profile.notify_by_phone:

                phone_to = str(o.user.username)
                sms_result = send_sms(msg, phone_to)
                logging.info('sms res: {}'.format(str(sms_result)))

            # send email
            if profile.notify_by_email:
                email = send_email(user.email, title, msg)
                email.send()


@shared_task
def sell_order_release():
    # TODO:
    # This the task to release FUNDS for clients that
    # SELL BTC or other coins to US
    # 1. Auto release funds when coins are credited
    # 2. Move funds from user card to our card
    # 3. Notify admin if auto payment is not available
    # for the payment preference that the user has selected.
    pass


@shared_task
def exchange_order_release():
    # TODO:
    # This the task to release COINS for clients that
    # EXCHANGE crypto-currencies, I.E. ETH to BTC
    # 1. Auto release funds when coins are credited
    # 2. Move funds from user card to our card
    # 3. Notify admin if auto payment is not available
    # for the payment preference that the user has selected.
    pass
