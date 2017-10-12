from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Reserve


class ReserveBalanceMaintainer(BaseAccountManagerTask):

    def run(self, reserve_id):
        reserve = Reserve.objects.get(pk=reserve_id)
        self.update_reserve_accounts_balances(reserve)
        trade_info = reserve.needed_trade_move
        trade_type = trade_info.get('trade_type')
        trade_amount = trade_info.get('amount')
        if trade_type:
            self.logger.info('Going to {} {} {}'.format(
                trade_type, str(trade_amount), reserve.currency.code))
            pair = self.get_traded_pair(reserve)
            account_dict = self.get_best_price_reserve_account(
                reserve, pair, trade_type)
            account = account_dict.get('account')
            rate = account_dict.get('rate')
            self.trade_coin(account, trade_type, trade_amount, pair, rate=rate)
            self.update_reserve_accounts_balances(reserve)
