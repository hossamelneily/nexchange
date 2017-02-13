from .base import BaseBuyOrderRelease
from orders.models import Order
from django.db import transaction


class BuyOrderReleaseByReference(BaseBuyOrderRelease):
    def get_order(self, payment):
        try:
            order = Order.objects.exclude(status=Order.RELEASED)\
                .get(unique_reference=payment.reference)
            if order.payment_preference.payment_method != \
                    payment.payment_preference.payment_method:

                if order.moderator_flag is not payment.pk:
                    self.logger.warn('Payment: {} Order: {} match exists'
                                     'but payment methods do not correspond '
                                     'Flagged for moderation - IGNORING'
                                     .format(order, payment))

                # MHM... Odd
                # Todo: unite flags somehow
                order.flag()
                payment.flag()
                return False

            if not payment.user or not payment.payment_preference.user:
                user = order.user
                with transaction.atomic(using='default'):
                    payment.user = user
                    payment.payment_preference.user = user
                    payment.save()
                    payment.payment_preference.save()
            elif payment.user != order.user:
                self.logger.warn('payment {} user {} users don\'t match '
                                 'is it a new user with old preference?'
                                 .format(payment, order))
                return False

            if not order.withdraw_address:
                self.logger.info('{} has now withdrawal address, moving on'
                                 .format(order.unique_reference))
                return False

            self.logger.info(
                'Found order {} with payment {} '
                .format(order.unique_reference, payment)
            )
            return order

        except Order.DoesNotExist:
            self.logger.info('Order for payment {} not found through ID'
                             ' or SmartMatching, '
                             'initiating BuyOrderReleaseByWallet'
                             .format(payment))
            self.add_next_task(BaseBuyOrderRelease.RELEASE_BY_WALLET,
                               [payment.pk])
            return False


class BuyOrderReleaseByWallet(BaseBuyOrderRelease):
    def get_order(self, payment):
        # Auto order payment
        # or user forgot reference
        # or uses out payout
        # feature
        try:
            method = payment.payment_preference.payment_method
            if payment.user and payment.payment_preference:
                return Order.objects.exclude(status=Order.RELEASED)\
                    .get(
                        user=payment.user,
                        amount_quote=payment.amount_cash,
                        payment_preference__payment_method=method,
                        pair__quote=payment.currency)
            else:
                    flag, new_flag = payment.flag(__name__)
                    if new_flag:
                        self.logger.warn('could not associate payment {}'
                                         ' with an order. '
                                         'owner user of wallet '
                                         '{} not found. '
                                         'SmartMatching disabled.'
                                         .format(payment,
                                                 method))
                    payment.save()

        except Order.DoesNotExist:
            self.logger.info.error('order for payment {} not found'
                                   ' through ID or SmartMatching, initiating '
                                   'BuyOrderReleaseByRule'
                                   .format(payment))
            self.add_next_task(BaseBuyOrderRelease.RELEASE_BY_RULE,
                               [payment.pk])
            return False


class BuyOrderReleaseByRule(BuyOrderReleaseByWallet):
    def get_order(self, payment):
        try:
            method = payment.payment_preference.payment_method
            template_order = Order.objects.filter(
                order_type=Order.BUY,
                is_redeemed=True,
                is_default_rule=True,
                user=payment.user,
                currency=payment.currency,
                payment__payment_preference__payment_method=method
            ).latest('id')

            new_order = Order(
                order_type=template_order.order_type,
                currency=template_order.currency,
                amount_qoute=payment.amount_cash,
                user=template_order.user,
                payment_preference=template_order.payment_preference,
            )

            new_order.save()

            return new_order

        except Order.DoesNotExist:
            flag, new_flag = payment.flag(__name__)
            if new_flag:
                self.error('Payment {} no default order,'
                           ' this payment is flagged'.format(payment))

        def complete_missing_data(self, payment, order):
            if not payment.user:
                payment.user = order.user
                payment.save()
                self.logger.info('Payment: {} Order: {} Set Payment.user'
                                 'from order').format(payment, order)

            if not payment.payment_preference.user:
                payment.payment_preference.user = order.user
                payment.payment_preference.save()
                self.logger.info('Payment: {} Order: {} Set PaymentPreference '
                                 'user from order').format(payment, order)
