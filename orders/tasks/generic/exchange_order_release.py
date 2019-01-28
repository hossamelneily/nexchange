from django.db import transaction
from core.models import Transaction
from orders.models import Order, LimitOrder
from orders.tasks.generic.base import BaseOrderRelease
from nexchange.api_clients.mixins import UpholdBackendMixin, ScryptRpcMixin
from nexchange.api_clients.factory import ApiClientFactory


class ExchangeOrderRelease(BaseOrderRelease, ApiClientFactory):
    UPDATE_TRANSACTIONS = \
        'accounts.task_summary.update_pending_transactions_invoke'

    BALANCE_UPDATE = \
        'risk_management.task_summary.currency_reserve_balance_checker_invoke'

    def _get_order(self, tx):

        order = tx.order if tx.order else tx.limit_order
        # TODO: move this logic to validate?
        if not order or order.flagged or not order.withdraw_address \
                or not order.exchange or order.status != Order.PAID \
                or bool(tx.order) == bool(tx.limit_order):
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
        if order.order_type == order.BUY or (
                order.order_type == order.SELL and isinstance(order,
                                                              LimitOrder)):
            self.traded_currency = currency = order.withdraw_currency
            amount = order.withdraw_amount

        else:
            self.logger.error('Bad order Type')
            return

        self.api = self.get_api_client(currency.wallet)
        order.refresh_from_db()
        if order.status not in order.IN_RELEASED:
            pre_release_res = order.pre_release(api=self.api)
            pre_release_status_ok = pre_release_res.get('status') == 'OK'
            if not pre_release_status_ok:
                return

            # Exclude because - transactions without type is possible
            tx_data = {
                'address_to': order.withdraw_address,
                'amount': amount,
                'currency': currency,
                'type': Transaction.WITHDRAW
            }
            if isinstance(order, Order):
                tx_data.update({'order': order})
            elif isinstance(order, LimitOrder):
                tx_data.update({'limit_order': order})

            if order.withdraw_currency.code == 'XRP':
                tx_data['destination_tag'] = order.destination_tag
            if order.withdraw_currency.code == 'XMR':
                tx_data['payment_id'] = order.payment_id
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
            'RELEASED order: {}, released transaction: {}'.format(
                order, txn
            )
        )

        return True

    def run(self, transaction_id):
        tx = Transaction.objects.get(pk=transaction_id)
        tx, order = self._get_order(tx)
        if order:
            self.logger.info('Release order {}'.format(order.unique_reference))
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
                    self.add_next_task(
                        self.BALANCE_UPDATE, [order.pair.base.code]
                    )
        else:
            self.logger.info('{} match order returned None'
                             .format(self.__class__.__name__))


class ExchangeOrderReleaseUphold(ExchangeOrderRelease, UpholdBackendMixin):
    pass


class ExchangeOrderReleaseScrypt(ExchangeOrderRelease, ScryptRpcMixin):
    pass
