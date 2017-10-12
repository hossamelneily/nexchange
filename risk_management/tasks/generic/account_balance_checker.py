from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Account


class AccountBalanceChecker(BaseAccountManagerTask):

    def run(self, account_id):
        try:
            account = Account.objects.get(pk=account_id)
            self.update_account_balance(account)
        except Account.DoesNotExist:
            self.logger.info('Account with pk {} not found'.format(account_id))
