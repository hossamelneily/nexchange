from nexchange.utils import release_payment
from django.db import transaction
from django.conf import settings
from core.models import Transaction
from orders.models import Order
from orders.tasks.generic.base import BaseOrderRelease


class ExchangeOrderRelease(BaseOrderRelease):
    UPDATE_TRANSACTIONS = \
        'accounts.task_summary.update_pending_transactions_invoke'

    def get_order(self, transaction):
        order = transaction.order
        if order.withdraw_address is None:
            return False
        if order is None:
            return False
        if not order.exchange:
            return False
        return order

    def validate(self, order, transaction):
        order_already_released = (
            order.status == Order.RELEASED
        )

        if order_already_released:
            flag, created = order.flag(__name__)
            if created:
                self.logger.error('order: {} transaction: {} ALREADY RELEASED'
                                  .format(order, transaction))
        transaction_ok = transaction.is_completed and transaction.is_verified

        return not order_already_released and transaction_ok

    def do_release(self, order):
        with transaction.atomic(using='default'):
            if order.order_type == Order.BUY:
                self.type_ = order.pair.base.code
                amount = order.amount_base
            elif order.order_type == Order.SELL:
                self.type_ = order.pair.quote.code
                amount = order.amount_quote
            tx_id = release_payment(order.withdraw_address, amount, self.type_)

            if tx_id is None:
                self.logger.error('Uphold Payment release returned None, '
                                  'order {}'.format(order))
                return False

            self.logger.info(
                'RELEASED order: {}, released tx_id: {}'.format(
                    order, tx_id
                )
            )

            if order.status not in Order.IN_RELEASED:
                order.status = Order.RELEASED
                order.save()

            t = Transaction(tx_id_api=tx_id, order=order,
                            address_to=order.withdraw_address)
            t.save()

            return True

    def run(self, transaction_id):
        transaction = Transaction.objects.get(pk=transaction_id)
        order = self.get_order(transaction)
        if order:
            if self.validate(order, transaction):
                if self.do_release(order):
                    self.notify(order)
                    countdown = getattr(
                        settings, '{}_CONFIRMATION_TIME'.format(self.type_)
                    )
                    self.immediate_apply = True
                    self.add_next_task(
                        self.UPDATE_TRANSACTIONS,
                        None,
                        {
                            'countdown': countdown
                        }
                    )
        else:
            self.logger.info('{} match order returned None'
                             .format(self.__class__.__name__))
