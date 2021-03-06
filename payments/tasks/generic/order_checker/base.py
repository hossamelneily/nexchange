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
        flagged_kycs = pref.verification_set.filter(flagged=True)
        paid = payment.is_success
        has_kyc = pref.is_verified
        whitelisted = order.withdraw_address in pref.whitelisted_addresses
        out_of_limit = pref.out_of_limit and not whitelisted
        name_matches = pref.name_on_card_matches

        is_immediate = pref.is_immediate_payment

        with transaction.atomic():
            if all([paid, has_kyc, is_immediate, not out_of_limit,
                    name_matches, not flagged_kycs]):
                confirm_res = order.confirm_deposit(payment, crypto=False)
                order.refresh_from_db()
                confirm_status_ok = confirm_res.get('status') == 'OK'
                if not confirm_status_ok:
                    self.logger.warning(
                        'Order {} deposit confirmation failed. res: {}'.format(
                            order.unique_reference, confirm_res
                        )
                    )
