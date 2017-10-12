from nexchange.tasks.base import BaseTask
from nexchange.api_clients.factory import ApiClientFactory
from core.models import Pair
from decimal import Decimal


class BaseAccountManagerTask(BaseTask, ApiClientFactory):

    def trade_coin(self, account, trade_type, amount, pair, rate=None):
        api = self.get_api_client(account.wallet)
        res = api.trade_limit(pair, amount, trade_type, rate=rate)
        self.logger.info('Trade finished: {} {} {}. res:{}'.format(
            trade_type, amount, pair, res
        ))
        return res

    def update_account_balance(self, account):
        api = self.get_api_client(account.wallet)
        balance_res = api.get_balance(account.reserve.currency)

        if isinstance(balance_res, dict):
            for attr, value in balance_res.items():
                setattr(account, attr, value)
        else:
            account.balance = account.available = Decimal(str(balance_res))
        account.save()

    def update_reserve_accounts_balances(self, reserve):
        for account in reserve.account_set.all():
            error_msg = 'Cannot update account {} balance. error: {}'
            try:
                self.update_account_balance(account)
            except ValueError as e:
                self.logger.info(error_msg.format(account, e))
            except Exception as e:
                self.logger.info(error_msg.format(account, e))

    def get_traded_pair(self, reserve):
        pair = Pair.objects.get(base=reserve.currency, quote__code='BTC')
        return pair

    def get_best_price_reserve_account(self, reserve, pair, trade_type):
        accounts = reserve.account_set.filter(trading_allowed=True)
        rate_list = []
        for account in accounts:
            api = self.get_api_client(account.wallet)
            rate_type = api.trade_type_rate_type_mapper(trade_type)
            rate = api.get_rate(pair, rate_type=rate_type)
            rate_list.append({'account': account, 'rate': rate})
        if trade_type == 'SELL':
            account_dict = max(rate_list, key=lambda x: x['rate'])
        elif trade_type == 'BUY':
            account_dict = min(rate_list, key=lambda x: x['rate'])

        return account_dict

    def send_funds_to_main_account(self, account, amount):
        api = self.get_api_client(account.wallet)
        currency = account.reserve.currency
        main_account_address = api.coin_address_mapper(currency.code)
        self.update_account_balance(account)
        account.refresh_from_db()
        if account.balance < amount:
            diff = (amount - account.balance)
            pair = Pair.objects.get(name='{}BTC'.format(currency.code))
            res = self.trade_coin(account, 'BUY', diff, pair)
            self.logger.info('Result of coint trade: {}'.format(res))
        res = api.release_coins(currency.code, main_account_address,
                                amount)
        self.update_account_balance(account)
        return res
