from django.db import transaction
from core.models import Transaction
from orders.models import Order
from orders.tasks.generic.base import BaseOrderRelease
from nexchange.api_clients.mixins import UpholdBackendMixin, ScryptRpcMixin
from nexchange.api_clients.uphold import UpholdApiClient
from nexchange.api_clients.rpc import ScryptRpcApiClient


class ExchangeOrderRelease(BaseOrderRelease):
    UPDATE_TRANSACTIONS = \
        'accounts.task_summary.update_pending_transactions_invoke'

    def _get_order(self, tx):
        order = tx.order
        # TODO: move this logic to validate?
        if not order or not order.withdraw_address \
                or not order.exchange or order.status != Order.PAID:
            return None, None

        return tx, order

    def validate(self, order, tx):
        order_already_released = order.status in Order.IN_RELEASED

        if order_already_released:
            flag, created = order.flag(__name__)
            if created:
                self.logger.error('order: {} transaction: {} ALREADY RELEASED'
                                  .format(order, tx))
        transaction_ok = tx.is_completed and tx.is_verified

        return not order_already_released and transaction_ok

    def do_release(self, order, payment=None):
        with transaction.atomic(using='default'):
            if order.order_type == Order.BUY:
                self.traded_currency = order.pair.base
                amount = order.amount_base
                currency = order.pair.base
            elif order.order_type == Order.SELL:
                self.traded_currency = order.pair.quote
                amount = order.amount_quote
                currency = order.pair.quote
            else:
                self.logger.error('Amount and Coin are None')
                return

            if currency.wallet == 'api1':
                self.api = UpholdApiClient()
            elif currency.wallet == 'rpc1':
                self.api = ScryptRpcApiClient()
            order.refresh_from_db()
            if order.status not in Order.IN_RELEASED:
                order.status = Order.RELEASED
                order.save()
                tx_id = self.api.release_coins(
                    currency,
                    order.withdraw_address,
                    amount
                )
            else:
                msg = 'Order {} already released'.format(order)
                self.logger.error(msg)
                return False

            if tx_id is None:
                msg = 'Uphold Payment release returned None, order {}'.format(
                    order)
                self.logger.error(msg)
                order.flag(val=msg)
                return False

            self.logger.info(
                'RELEASED order: {}, released tx_id: {}'.format(
                    order, tx_id
                )
            )

            transaction_data = {'order': order,
                                'address_to': order.withdraw_address,
                                'amount': amount,
                                'currency': currency,
                                'type': Transaction.WITHDRAW}
            if currency.wallet == 'api1':
                transaction_data.update({'tx_id_api': tx_id})
            elif currency.wallet == 'rpc1':
                transaction_data.update({'tx_id': tx_id})
            t = Transaction(**transaction_data)
            t.save()

            return True

    def run(self, transaction_id):
        tx = Transaction.objects.get(pk=transaction_id)
        tx, order = self._get_order(tx)
        if order:
            if self.validate(order, tx):
                if self.do_release(order):
                    self.immediate_apply = True
                    self.add_next_task(
                        self.UPDATE_TRANSACTIONS,
                        None,
                        {
                            'countdown': self.traded_currency.median_confirmation * 60  # noqa
                        }
                    )
        else:
            self.logger.info('{} match order returned None'
                             .format(self.__class__.__name__))


class ExchangeOrderReleaseUphold(ExchangeOrderRelease, UpholdBackendMixin):
    pass


class ExchangeOrderReleaseScrypt(ExchangeOrderRelease, ScryptRpcMixin):
    pass
