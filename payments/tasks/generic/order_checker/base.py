from __future__ import absolute_import
from nexchange.tasks.base import BaseTask

from orders.models import Order
from payments.models import Payment
from django.db import transaction


class BaseFiatOrderDepositChecker(BaseTask):

    def run(self, order_pk):
        order = Order.objects.get(pk=order_pk)

        payment = order.payment_set.get(type=Payment.DEPOSIT)
        pref = payment.payment_preference
        paid = payment.is_success
        has_kyc = pref.is_verified
        out_of_limit = pref.out_of_limit
        whitelisted = \
            not pref.tier.whitelisting_required \
            or order.withdraw_address in pref.whitelisted_addresses

        is_immediate = pref.is_immediate_payment

        with transaction.atomic():
            if all([paid, has_kyc, is_immediate, not out_of_limit,
                    whitelisted]):
                confirm_res = order.confirm_deposit(payment, crypto=False)
                order.refresh_from_db()
                confirm_status_ok = confirm_res.get('status') == 'OK'
                if not confirm_status_ok:
                    self.logger.warning(
                        'Order {} deposit confirmation failed. res: {}'.format(
                            order.unique_reference, confirm_res
                        )
                    )
