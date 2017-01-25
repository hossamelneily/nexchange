from __future__ import absolute_import
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from core.models import Transaction
from nexchange.utils import check_transaction_blockchain, \
    check_transaction_uphold, send_email, send_sms
import logging


@shared_task
def update_transaction_confirmations():
    for tr in Transaction.objects.\
            filter(Q(is_completed=False) | Q(is_verified=False)):
        order = tr.order
        profile = order.user.profile
        logging.info(
            'Look-up transaction with txid api {} '.format(tr.tx_id_api))
        if check_transaction_uphold(tr):
            tr.is_completed = True
            tr.save()
            order.is_completed = True
            order.save()

        if check_transaction_blockchain(tr):
            tr.is_verified = True
            tr.save()

            title = _('Nexchange: Order released')
            msg = _('Your order {}:  is released'). \
                format(tr.order.o.unique_reference)

            if profile.notify_by_phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    logging.info(str(sms_result))

            if profile.notify_by_email:
                email = send_email(tr.order.user.email, title, msg)
                email.send()

            if settings.DEBUG:
                logging.info('Transaction {} is completed'.format(tr.tx_id))
