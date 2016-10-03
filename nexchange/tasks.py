from __future__ import absolute_import

from celery import shared_task
import logging
from core.models import Payment, Order, Transaction, Address
from django.utils.translation import ugettext_lazy as _
from nexchange.utils import send_sms, release_payment, checktransaction


logging.basicConfig(filename='payment_release.log', level=logging.INFO)


@shared_task
def payment_release():
    for o in Order.objects.filter(is_paid=True, is_released=False):
        print("Look order {} ".format(o.unique_reference))
        p = Payment.objects.filter(user=o.user,
                                   amount_cash=o.amount_cash,
                                   payment_preference=o.payment_preference,
                                   is_complete=False,
                                   currency=o.currency).first()
        if p is not None:
            tx_id_ = release_payment(o.withdraw_address,
                                     o.amount_btc)

            if tx_id_ is None:
                continue

            o.is_released = True
            o.save()

            p.is_complete = True
            p.save()
            # #
            # send sms depending on notification settings in profile
            msg = _("Your order {}:  is released").format(o.unique_reference)

            phone_to = str(o.user.username)

            sms_result = send_sms(msg, phone_to)
            print(str(sms_result))

            # send email
            # email = EmailMessage('title', msg, to=[email])
            # email.send()

            print(tx_id_)
            adr = Address.objects.get(
                user=o.user, address=o.withdraw_address)

            t = Transaction(tx_id=tx_id_, order=o, address_to=adr)
            t.save()

        else:
            print('payment not found ')


@shared_task
def checker_transactions():
    for tr in Transaction.objects.filter(is_completed=False):
        print("Look transaction {} ".format(tr.tx_id))
        if checktransaction(tr.tx_id):
            tr.is_completed = True
            tr.save()

            msg = _("Your order {}:  is released").\
                format(tr.order.o.unique_reference)
            phone_to = str(tr.order.user.username)

            sms_result = send_sms(msg, phone_to)
            print(str(sms_result))

            print("Transaction {} is completed".format(tr.tx_id))
