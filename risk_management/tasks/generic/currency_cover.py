from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Cover
from core.models import Currency


class CurrencyCover(BaseAccountManagerTask):

    # FIXME: Should be removed after all coins trading works
    ALLOWED_COINS = ['XVG']

    def run(self, currency_code, amount):
        # FIXME: Should be removed after all coins trading works
        if currency_code not in self.ALLOWED_COINS:
            self.logger.info(
                'Do not create Cover. Currency {} is not in '
                'ALLOWED_COINS list {}'.format(currency_code,
                                               self.ALLOWED_COINS)
            )
            return
        currency = Currency.objects.get(code=currency_code)
        reserve = currency.reserve_set.get()

        cover = Cover(amount_base=amount, currency=currency)
        cover.save()

        trade_type = 'BUY'
        trade_amount = cover.amount_base
        self.logger.info('Going to {} {} {}'.format(
            trade_type, str(trade_amount), currency.code))
        cover.pair = self.get_traded_pair(reserve)
        account_dict = self.get_best_price_reserve_account(
            reserve, cover.pair, trade_type)
        cover.account = account_dict.get('account')
        cover.rate = account_dict.get('rate')
        cover.amount_quote = cover.amount_base * cover.rate
        cover.save()
        res = self.trade_coin(cover.account, trade_type, trade_amount,
                              cover.pair, rate=cover.rate)
        cover.cover_id = res.get('result', {}).get('uuid')
        cover.save()
        return cover
