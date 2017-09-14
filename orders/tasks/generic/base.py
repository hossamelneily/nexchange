from nexchange.tasks.base import BaseApiTask
from payments.models import Payment
from django.db import transaction
from core.models import Transaction
from orders.models import Order


class BaseOrderRelease(BaseApiTask):
    @classmethod
    def get_order(cls, payment_id):
        return Payment.objects.get(pk=payment_id), None

    def _get_order(self, payment):
        raise NotImplementedError

    def complete_missing_data(self, payment, order):
        pass

    def validate(self, order, payment):
        order_already_released = (payment.is_redeemed or
                                  order.status in Order.IN_RELEASED)

        if order_already_released:
            flag, created = order.flag(__name__)
            if created:
                self.logger.error('order: {} payment: {} ALREADY RELEASED'
                                  .format(order, payment))

        if not payment.is_success:
            flag, created = payment.flag(__name__)
            if created:
                self.logger.warn('order: {} payment: {} IS NOT SUCCESS'
                                 .format(order, payment))

        return not order_already_released and payment.is_success

    def do_release(self, order, payment):
        raise NotImplementedError

    def run(self, payment_id):
        ret = self._get_order(payment_id)
        if isinstance(ret, bool):
            self._get_order(payment_id)
        payment, order = ret
        if order:
            if self.validate(order, payment):
                if self.do_release(order, payment):
                    self.complete_missing_data(payment, order)
        else:
            payment = Payment.objects.get(pk=payment_id)
            self.logger.error('{} match order returned None, Payment:{}'
                              .format(self.__class__.__name__, payment))
            payment.flag(val='Payment ({}) match order returned None'.format(
                payment)
            )

        super(BaseOrderRelease, self).run(payment_id)


class BaseBuyOrderRelease(BaseOrderRelease):
    RELEASE_BY_REFERENCE = \
        'orders.task_summary.buy_order_release_by_reference_invoke'
    RELEASE_BY_WALLET = \
        'payments.task_summary.buy_order_release_by_wallet_invoke'
    RELEASE_BY_RULE = \
        'payments.task_summary.buy_order_release_by_rule_invoke'

    def do_release(self, order, payment):
        with transaction.atomic(using='default'):
            payment.is_complete = True
            payment.save()
            # type_ = order.pair.base.code
            order.refresh_from_db()
            if order.status not in Order.IN_RELEASED:
                order.pre_release()
                currency = order.pair.base
                tx_data = {'order': order,
                           'address_to': order.withdraw_address,
                           'amount': order.amount_base,
                           'currency': currency,
                           'type': Transaction.WITHDRAW}
                release_res = order.release(tx_data, api=self.api)
                release_status_ok = release_res.get('status') == 'OK'
                if not release_status_ok:
                    error_msg = release_res.get('message')
                    msg = 'Order {} is not RELEASED. Msg: {}'.format(
                        order.unique_reference, error_msg)
                    self.logger.error(msg)
                    return False

            else:
                msg = 'Order {} already released'.format(order)
                self.logger.error(msg)
                order.flag(val=msg)
                return False

            txn = release_res.get('txn')
            self.logger.info(
                'RELEASED order: {}, Payment: {}, released '
                'transaction: {}'.format(order, payment, txn)
            )

            payment.is_redeemed = True
            payment.order = order
            payment.save()

            return True

    def validate(self, order, payment):
        # hack to prevent circular imports
        verbose_match = type(self).__name__ == 'BuyOrderReleaseByWallet'
        details_match = order.pair.quote == payment.currency
        ref_matches = order.unique_reference == payment.reference or \
            verbose_match

        user_matches = not payment.user or payment.user == order.user

        order_paid = order.is_paid

        verification_passed = payment.payment_preference.user_verified_for_buy

        if verbose_match and payment.reference:
            payment.flag(__name__)
            self.logger.warn('order: {} payment: {} '
                             'USER ENTERED INCORRECT REF'
                             'FALLING BACK TO CrossCheck RELEASE'
                             .format(order, payment))

        if not order_paid:
            self.logger.error('Cannot release Order({}) which is not '
                              'Paid'.format(order))
        if not user_matches:
            self.logger.error('order: {} payment: {} NO USER MATCH'
                              .format(order, payment))
        if not details_match:
            self.logger.error('order: {} payment: {} NO DETAILS MATCH'
                              .format(order, payment))
        if not ref_matches:
            self.logger.error('order: {} payment: {} NO REFERENCE MATCH'.
                              format(order, payment))
        elif verbose_match:
            self.logger.info('order: {} payment: {} NO REFERENCE MATCH,'
                             'RELEASE BY VERBOSE_MATCH (cross reference)'.
                             format(order, payment))

        match = user_matches and details_match and ref_matches and order_paid\
            and verification_passed

        if match:
            self.logger.info('Order {}  VALID {}'
                             .format(order, order.withdraw_address))
        else:
            # NOTE: Maybe it should not be flagged if ref_matches==False?
            # (To release with different tasks)
            msg = 'order({}) and payment{} doesn\'t match.'.format(order,
                                                                   payment)
            desc = \
                'user_matches=={}, details_match=={}, ref_matches=={}, ' \
                'order_paid=={}, verification_passed=={}'.format(
                    user_matches, details_match, ref_matches, order_paid,
                    verification_passed
                )
            order.flag(val=msg + desc)
            payment.flag(val=msg + desc)

        return match and super(BaseBuyOrderRelease, self)\
            .validate(order, payment)
