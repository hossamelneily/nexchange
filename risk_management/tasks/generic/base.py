from nexchange.tasks.base import BaseTask
from nexchange.api_clients.factory import ApiClientFactory
from core.models import Pair, Transaction, Address
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
        try:
            balance_res = api.get_balance(account.reserve.currency)
            if isinstance(balance_res, dict):
                for attr, value in balance_res.items():
                    setattr(account, attr, value)
            else:
                account.balance = account.available = Decimal(str(balance_res))
            account.healthy = True
        except Exception as e:
            self.logger.info('Smth is wrong with \'{}.get_balance\': {}'.
                             format(api.__class__.__name__, e))
            account.healthy = False
        account.save()

    def update_reserve_accounts_balances(self, reserve):
        for account in reserve.account_set.filter(disabled=False):
            error_msg = 'Cannot update account {} balance. error: {}'
            try:
                self.update_account_balance(account)
            except ValueError as e:
                self.logger.info(error_msg.format(account, e))
            except Exception as e:
                self.logger.info(error_msg.format(account, e))

    def get_traded_pair(self, currency, counter_currency_code=None):
        if counter_currency_code is None \
                or counter_currency_code not in ['BTC', 'ETH', 'LTC']:
            counter_currency_code = 'BTC'
        if currency.is_crypto:
            return Pair.objects.get(
                base=currency, quote__code=counter_currency_code)
        else:
            return Pair.objects.get(
                base__code=counter_currency_code, quote__code='EUR')

    def get_best_price_reserve_account(self, reserve, pair, trade_type,
                                       required_rate=None):
        accounts = reserve.account_set.filter(trading_allowed=True)
        rate_list = []
        for account in accounts:
            api = self.get_api_client(account.wallet)
            rate_type = api.trade_type_rate_type_mapper(trade_type)
            rate = api.get_rate(pair, rate_type=rate_type)
            rate_list.append({'account': account, 'rate': rate})
        if trade_type == 'SELL':
            account_dict = max(rate_list, key=lambda x: x['rate'])
            if required_rate is not None:
                account_dict['rate'] = max(required_rate, account_dict['rate'])
        elif trade_type == 'BUY':
            account_dict = min(rate_list, key=lambda x: x['rate'])
            if required_rate is not None:
                account_dict['rate'] = min(required_rate, account_dict['rate'])
        return account_dict

    def send_funds_to_main_account(self, account, amount=None, do_trade=False):
        currency = account.reserve.currency
        currency_api = self.get_api_client(currency.wallet)
        assert currency_api.health_check(currency)
        self.update_account_balance(account)
        account.refresh_from_db()
        if not amount:
            amount = account.available
        elif account.available < amount and do_trade:
            diff = (amount - account.balance)
            pair = Pair.objects.get(name='{}BTC'.format(currency.code))
            res = self.trade_coin(account, 'BUY', diff, pair)
            self.logger.info('Result of coin trade: {}'.format(res))
        main_account = currency.reserve.main_account
        res = self.transfer(currency, account, main_account, amount)
        self.update_account_balance(account)
        return res

    def _assert_account_currency(self, currency, account):
        assert currency == account.reserve.currency,\
            'transfer currency {} but account pk {}_currency is {}'.format(
                currency.code,
                account.pk,
                account.reserve.currency.code
            )

    def get_or_create_internal_address(self, _address, currency):
        address, success = Address.objects.get_or_create(
            address=_address, currency=currency, type=Address.INTERNAL
        )
        return address

    def _create_internal_tx_obj(self, currency, address_to, amount):
        tx = Transaction(
            currency=currency,
            amount=amount,
            address_to=address_to,
            type=Transaction.INTERNAL
        )
        tx.save()
        return tx

    def transfer(self, currency, account_from, account_to, amount):
        self._assert_account_currency(currency, account_from)
        self._assert_account_currency(currency, account_to)
        api_from = self.get_api_client(account_from.wallet)
        api_to = self.get_api_client(account_to.wallet)
        assert api_from.health_check(currency)
        assert api_to.health_check(currency)
        _address = api_to.get_main_address(currency)
        assert _address
        address_to = self.get_or_create_internal_address(_address, currency)
        tx = self._create_internal_tx_obj(currency, address_to, amount)
        tx_id, success = api_from.release_coins(currency, address_to, amount)
        if success:
            tx.tx_id = tx_id
            tx.is_verified = True
            tx.is_completed = True
            tx.save()
        else:
            tx.flag(val='error while making internal transfer')
        return tx
