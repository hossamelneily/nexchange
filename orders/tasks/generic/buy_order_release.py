from django.conf import settings
from django.db import transaction

from nexchange.api_clients.mixins import UpholdBackendMixin, ScryptRpcMixin
from orders.models import Order
from .base import BaseBuyOrderRelease


class BuyOrderReleaseByReference(BaseBuyOrderRelease):
    @classmethod
    def get_order(cls, payment_id):
        payment, order = super(BuyOrderReleaseByReference, cls).get_order(
            payment_id)
        return payment, Order.objects.exclude(status=Order.RELEASED).exclude(
            status=Order.COMPLETED).get(unique_reference=payment.reference)

    def _get_order(self, payment):
        try:
            payment, order = self.get_order(payment)
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
                self.logger.error(
                    'payment {} user {} users don\'t match is it a new user '
                    'with old preference?'.format(payment, order)
                )
                msg = 'order({}) and payment{} doesn\'t match.'.format(order,
                                                                       payment)
                desc = 'order.user!=payment.user'
                order.flag(val=msg + desc)
                payment.flag(val=msg + desc)
                return None, None

            if not order.withdraw_address:
                self.logger.info('{} has now withdrawal address, moving on'
                                 .format(order.unique_reference))
                self.add_next_task(
                    BaseBuyOrderRelease.RELEASE_BY_REFERENCE,
                    [order.pk],
                    {
                        'countdown':
                            settings.USER_SETS_WITHDRAW_ADDRESS_MEDIAN_TIME
                    }
                )
                return None, None

            self.logger.info(
                'Found order {} with payment {} '
                .format(order.unique_reference, payment)
            )
            return payment, order

        except Order.DoesNotExist:
            self.logger.info('Order for payment {} not found through ID'
                             ' or SmartMatching, '
                             'initiating BuyOrderReleaseByWallet'
                             .format(payment))
            self.add_next_task(BaseBuyOrderRelease.RELEASE_BY_WALLET,
                               [payment])
            return None, None


class BuyOrderReleaseByWallet(BaseBuyOrderRelease):
    @classmethod
    def get_order(cls, payment_id):
        payment, order = super(BuyOrderReleaseByWallet, cls).get_order(
            payment_id)

        method = payment.payment_preference.payment_method
        return payment,\
               Order.objects.exclude(status=Order.RELEASED).exclude(
                   status=Order.COMPLETED).get(
                   user=payment.user,
                   amount_quote=payment.amount_cash,
                   payment_preference__payment_method=method,
                   pair__quote=payment.currency)

    def _get_order(self, payment):
        # Auto order payment
        # or user forgot reference
        # or uses out payout
        # feature

        try:
            payment, order = self.get_order(payment)
            if payment.user and payment.payment_preference:
                return payment, order
            else:
                    flag, new_flag = payment.flag(__name__)
                    if new_flag:
                        self.logger.warn('could not associate payment {}'
                                         ' with an order. '
                                         'SmartMatching disabled.'
                                         .format(payment))
                    payment.save()

        except Order.DoesNotExist:
            self.logger.info('order for payment {} not found'
                             ' through ID or SmartMatching, initiating '
                             'BuyOrderReleaseByRule'
                             .format(payment))
            self.add_next_task(BaseBuyOrderRelease.RELEASE_BY_RULE,
                               [payment])
            return None, None


class BuyOrderReleaseByRule(BuyOrderReleaseByWallet):
    @classmethod
    def get_order(cls, payment_id):
        payment, order = super(BuyOrderReleaseByRule, cls).get_order(
            payment_id)
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
        return payment, new_order

    def _get_order(self, payment):
        try:
            return self.get_order(payment)
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


# UPHOLD COINS
class BuyOrderReleaseByReferenceUphold(BuyOrderReleaseByReference,
                                       UpholdBackendMixin):
    pass


class BuyOrderReleaseByWalletUphold(BuyOrderReleaseByWallet,
                                    UpholdBackendMixin):
    pass


class BuyOrderReleaseByRuleUphold(BuyOrderReleaseByRule,
                                  UpholdBackendMixin):
    pass


# SCRYPT RPC COINS
class BuyOrderReleaseByReferenceScrypt(BuyOrderReleaseByReference,
                                       ScryptRpcMixin):
    pass


class BuyOrderReleaseByWalletScrypt(BuyOrderReleaseByWallet,
                                    ScryptRpcMixin):
    pass


class BuyOrderReleaseByRuleScrypt(BuyOrderReleaseByRule,
                                  ScryptRpcMixin):
    pass
