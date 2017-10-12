from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Account
from decimal import Decimal


class MainAccountFiller(BaseAccountManagerTask):

    def run(self, account_id, amount):
        try:
            account = Account.objects.get(pk=account_id)
            amount = Decimal(str(amount))
            self.send_funds_to_main_account(account, amount)
        except Account.DoesNotExist:
            self.logger.info('Account with pk {} not found'.format(account_id))
