from django.db import transaction
from core.models import Transaction
from orders.models import Order
from orders.tasks.generic.base import BaseOrderRelease
from nexchange.api_clients.mixins import UpholdBackendMixin, ScryptRpcMixin
from nexchange.api_clients.factory import ApiClientFactory


class ExchangeOrderRelease(BaseOrderRelease, ApiClientFactory):
    UPDATE_TRANSACTIONS = \
        'accounts.task_summary.update_pending_transactions_invoke'

    BALANCE_UPDATE = \
        'risk_management.task_summary.currency_reserve_balance_checker_invoke'

    def _get_order(self, tx):
        order = tx.order
        # TODO: move this logic to validate?
        if order.flagged or not order or not order.withdraw_address \
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
            else:
                self.logger.error('Bad order Type')
                return

            self.api = self.get_api_client(currency.wallet)
            order.refresh_from_db()
            if order.status not in Order.IN_RELEASED:
                order.pre_release()
                # Exclude because - transactions without type is possible
                tx_data = {'order': order,
                           'address_to': order.withdraw_address,
                           'amount': amount,
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
