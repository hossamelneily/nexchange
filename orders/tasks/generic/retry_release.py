from nexchange.tasks.base import BaseApiTask
from core.models import Transaction
from orders.models import Order


class RetryOrderRelease(BaseApiTask):

    def validate_tx(self, tx):
        valid = all([not tx.is_verified, not tx.flagged, tx.order,
                     not tx.tx_id, tx.type == Transaction.WITHDRAW])
        return valid

    def validate_order(self, order, tx):
        tx_pk = tx.pk
        other_with_txs = order.transactions.filter(
            type=Transaction.WITHDRAW).exclude(pk=tx_pk)
        valid_tx_count = len(other_with_txs) == 0
        valid_status = order.status == Order.RELEASED
        valid_amount = order.amount_base == tx.amount
        valid_currency = order.pair.base == tx.currency
        valid_address = order.withdraw_address == tx.address_to
        valid_data = all([valid_amount, valid_currency, valid_address])
        valid = all([valid_tx_count, valid_status, valid_data])
        return valid

    def run(self, tx_pk):
        tx = Transaction.objects.get(pk=tx_pk)
        order = tx.order
        tx_valid = self.validate_tx(tx)
        if not tx_valid:
            msg = 'cannot release(retry) tx pk {} - tx is not valid'.format(
                tx.pk)
            self.logger.info(msg)
            return {'success': False, 'retry': False}
        order_valid = self.validate_order(order, tx)
        if not order_valid:
            msg = 'cannot release(retry) tx pk {} - order is not ' \
                  'valid'.format(tx.pk)
            self.logger.info(msg)
            return {'success': False, 'retry': False}
        return self.api.retry(tx)
