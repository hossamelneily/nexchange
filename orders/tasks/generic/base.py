from nexchange.tasks.base import BaseTask
from django.utils.translation import activate
from payments.models import Payment
from nexchange.utils import send_email, send_sms, release_payment
from django.db import transaction
from core.models import Address, Transaction
from orders.models import Order
from django.utils.translation import ugettext_lazy as _


class BaseOrderRelease(BaseTask):
    def __init__(self):
        super(BaseOrderRelease, self).__init__()

    def get_order(self, payment):
        raise NotImplementedError

    def complete_missing_data(self, payment, order):
        pass

    def get_profile(self, order):
        return order.user.profile

    def validate(self, order, payment):
        order_already_released = payment.order or payment.is_redeemed or \
            order.status == Order.RELEASED

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

    def notify(self, order):
        profile = self.get_profile(order)

        # Activate translation
        if any([profile.notify_by_email, profile.notify_by_phone]):
            activate(profile.lang)

        title = _(
            'Nexchange: Order {} released'.format(
                order.unique_reference))
        msg = _('Your order {}: is released. Withdraw address: {}') \
            .format(
            order.unique_reference,
            order.withdraw_address
        )
        self.logger.info('release message sent to client, title: {} | msg: {}'
                         .format(title, msg))

        # send sms depending on notification settings in profile
        if profile.notify_by_phone:
            phone_to = str(profile.phone)
            sms_result = send_sms(msg, phone_to)
            self.logger.info('sms res: {}'.format(str(sms_result)))

        # send email
        if profile.notify_by_email:
            send_email(profile.user.email, title, msg)

    def run(self, payment_id):
        payment = Payment.objects.get(pk=payment_id)
        order = self.get_order(payment)
        if not order:
            self.logger.info('{} match order returned None'
                             .format(self.__class__.__name__))

        if self.validate(order, payment):
            if self.do_release(order, payment):
                self.complete_missing_data(payment, order)
                self.notify(order)

        super(BaseOrderRelease, self).run(payment_id)


class BaseBuyOrderRelease(BaseOrderRelease):
    RELEASE_BY_WALLET = 'payments.task_summary.release_by_wallet'
    RELEASE_BY_RULE = 'payments.task_summary.release_by_rule'

    def do_release(self, order, payment):
        with transaction.atomic(using='default'):
            payment.is_complete = True
            payment.save()
            tx_id = release_payment(order.withdraw_address,
                                    order.amount_base)

            if tx_id is None:
                self.logger.error('Payment release returned None, '
                                  'order {} payment {}'.format(order,
                                                               payment))
                return False

            self.logger.info(
                'RELEASED order: {} with payment {} '
                'released tx id: {}'.format(
                    order, payment, tx_id
                )
            )

            order.status = Order.RELEASED
            order.save()

            payment.is_redeemed = True
            payment.order = order
            payment.save()

            # double check
            adr = Address.objects.get(
                user=order.user,
                address=order.withdraw_address.address
            )

            t = Transaction(tx_id_api=tx_id, order=order, address_to=adr)
            t.save()

            return True

    def validate(self, order, payment):
        # hack to prevent circular imports
        verbose_match = type(self).__name__ == 'BuyOrderReleaseByWallet'
        details_match = \
            order.pair.quote == payment.currency and \
            order.amount_quote == payment.amount_cash
        ref_matches = order.unique_reference == payment.reference or \
            verbose_match

        user_matches = not payment.user or payment.user == order.user

        if verbose_match and payment.reference:
            payment.flag(__name__)
            self.logger.warn('order: {} payment: {} '
                             'USER ENTERED INCORRECT REF'
                             'FALLING BACK TO CrossCheck RELEASE'
                             .format(order, payment))

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

        match = user_matches and details_match and ref_matches

        if match:
            self.logger.info('Order {}  VALID {}'
                             .format(order, order.withdraw_address))

        return match and super(BaseBuyOrderRelease, self)\
            .validate(order, payment)
