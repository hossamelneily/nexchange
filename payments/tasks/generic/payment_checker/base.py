from nexchange.tasks.base import BaseTask

from payments.models import Payment


class BasePaymentRefundChecker(BaseTask):

    def run(self, payment_pk):
        payment = Payment.objects.get(pk=payment_pk)

        paid = payment.is_success
        kyc_expired = payment.kyc_wait_refund_period_expired
        not_flagged = not payment.flagged

        if all([paid, kyc_expired, not_flagged]):
            order = payment.order
            msg = 'Refund due to no KYC and no email. Order {}'.format(
                order.unique_reference
            )
            payment.flag(val=msg)
            order.refund(refund_type='refund')
            self.logger.warning(msg)


class BasePaymentVoidChecker(BaseTask):

    def run(self, payment_pk):
        payment = Payment.objects.get(pk=payment_pk)

        paid = payment.is_success
        kyc_expired = payment.kyc_wait_void_period_expired

        if all([paid, kyc_expired]):
            order = payment.order
            msg = 'Void due to no KYC uploaded. Order {}'.format(
                order.unique_reference
            )
            payment.flag(val=msg)
            order.refund()
            self.logger.warning(msg)
