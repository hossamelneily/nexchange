from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Reserve


class ReserveBalanceChecker(BaseAccountManagerTask):

    def run(self, reserve_id):
        reserve = Reserve.objects.get(pk=reserve_id)
        self.update_reserve_accounts_balances(reserve)
