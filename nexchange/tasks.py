from __future__ import absolute_import

from celery import shared_task
import logging
from core.models import Order, Transaction, Address
from payments.models import Payment
from django.utils.translation import ugettext_lazy as _
from nexchange.utils import send_sms, send_email,\
    release_payment, check_transaction_uphold
from django.conf import settings

logging.basicConfig(filename='payment_release.log', level=logging.INFO)


@shared_task
def payment_release():
    # TODO: iterate over payments instead, will be much faster
    for o in Order.objects.filter(is_paid=True, is_released=False):
        if not o.has_withdraw_address:
            print("{} has now withdrawal address, moving on".
                  format(o.unique_reference))
            continue
        user = o.user
        profile = user.profile
        if settings.DEBUG:
            print("Look order {} ".format(o.unique_reference))
        p = Payment.objects.filter(user=user,
                                   amount_cash=o.amount_cash,
                                   payment_preference__payment_method=
                                   o.payment_preference.payment_method,
                                   is_redeemed=False,
                                   currency=o.currency).first()

        if p:
            print(o.withdraw_address)
            p.is_complete = True
            p.save()
            tx_id = release_payment(o.withdraw_address,
                                    o.amount_btc)

            if tx_id is None:
                continue

            print('tx id: {}'.format(tx_id))
            o.is_released = True
            o.save()

            p.is_redeemed = True
            p.save()

            adr = Address.objects.get(
                user=o.user, address=o.withdraw_address)

            t = Transaction(tx_id_api=tx_id, order=o, address_to=adr)
            t.save()

            msg = _("Your order {}:  is released").format(o.unique_reference)

            if settings.DEBUG:
                print(msg)

            # send sms depending on notification settings in profile
            if profile.notify_by_phone:
                phone_to = str(o.user.username)
                sms_result = send_sms(msg, phone_to)
                if settings.DEBUG:
                    print(str(sms_result))

            # send email
            if profile.notify_by_email:
                email = send_email(user.email, 'title', msg)
                email.send()

        elif settings.DEBUG:
            print('payment not found')


@shared_task
def checker_transactions():
    for tr in Transaction.objects.filter(is_completed=False):
        order = tr.order
        profile = order.user.profile
        if settings.DEBUG:
            print("Look-up transaction with txid api {} ".format(tr.tx_id_api))
        if check_transaction_uphold(tr):
            tr.is_completed = True
            tr.save()
            order.is_completed = True
            order.save()

            msg = _("Your order {}:  is released"). \
                format(tr.order.o.unique_reference)

            if profile.notify_by_phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    print(str(sms_result))

            if profile.notify_by_email:
                pass

            if settings.DEBUG:
                print("Transaction {} is completed".format(tr.tx_id))
