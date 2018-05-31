from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Account
from core.models import Currency
from orders.models import Order
from risk_management.models import ReservesCover
from decimal import Decimal


class InternalTransfersMaker(BaseAccountManagerTask):

    def run(self, currency_id, account_from_id, account_to_id, amount,
            order_id=None, reserves_cover_id=None):
        try:
            currency = Currency.objects.get(pk=currency_id)
            account_from = Account.objects.get(pk=account_from_id)
            account_to = Account.objects.get(pk=account_to_id)
            if amount:
                amount = Decimal(str(amount))
            tx = self.transfer(currency, account_from, account_to, amount)
            if order_id:
                tx.order = Order.objects.get(pk=order_id)
                tx.save()
            if reserves_cover_id:
                tx.reserves_cover = ReservesCover.objects.get(
                    pk=reserves_cover_id
                )
                tx.save()
            return tx
        except Account.DoesNotExist:
            self.logger.info(
                'Account with pk {} or not found'.format(account_to,
                                                         account_from)
            )
