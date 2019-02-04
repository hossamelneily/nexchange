from risk_management.tasks.generic.base import BaseAccountManagerTask
from risk_management.models import Cover
from core.models import Currency
from decimal import Decimal
from ticker.models import Price


class CurrencyCover(BaseAccountManagerTask):

    # FIXME: Should be removed after all coins trading works
    ALLOWED_COINS = ['XVG', 'ZEC']

    def run(self, currency_code, amount, counter_currency_code=None,
            required_rate=None):
        eur = Currency.objects.get(code='EUR')
        currency = Currency.objects.get(code=currency_code)
        cover_type = None
        use_quote = False
        if amount >= Decimal('0'):
            trade_type = 'BUY'
            cover_type = Cover.BUY
        elif amount < Decimal('0') and currency.is_crypto:
            trade_type = 'SELL'
            cover_type = Cover.SELL
        elif amount < Decimal('0') and not currency.is_crypto:
            trade_type = 'BUY'
            cover_type = Cover.BUY
            use_quote = True
        # FIXME: Should be removed after all coins trading works
        if currency_code not in self.ALLOWED_COINS and currency.is_crypto:
            self.logger.info(
                'Do not create Cover. Currency {} is not in '
                'ALLOWED_COINS list {}'.format(currency_code,
                                               self.ALLOWED_COINS)
            )
            return
        cover_currency = currency if currency.is_crypto else eur
        reserve = cover_currency.reserve

        cover = Cover(currency=cover_currency, cover_type=cover_type)
        if use_quote:
            cover.amount_quote = abs(amount)
            trade_amount = cover.amount_quote
        else:
            cover.amount_base = abs(amount)
            trade_amount = cover.amount_base
        cover.save()

        self.logger.info('Going to {} {} {}'.format(
            trade_type, str(trade_amount), currency.code))
        cover.pair = self.get_traded_pair(
            currency, counter_currency_code=counter_currency_code
        )
        if required_rate and not currency.is_crypto:
            base_multip = Price.convert_amount(
                Decimal('1'), counter_currency_code, cover.pair.base
            )
            quote_multip = Price.convert_amount(Decimal('1'), currency,
                                                cover.pair.quote)
            required_rate = required_rate * quote_multip / base_multip
            cover.amount_quote *= quote_multip

        account_dict = self.get_best_price_reserve_account(
            reserve, cover.pair, trade_type, required_rate=required_rate)
        cover.account = account_dict.get('account')
        cover.rate = account_dict.get('rate')
        if cover.amount_base:
            cover.amount_quote = cover.amount_base * cover.rate
        elif cover.amount_quote:
            cover.amount_base = cover.amount_quote / cover.rate
        cover.save()
        if currency.execute_cover:
            cover.pre_execute()
            api = self.get_api_client(cover.account.wallet)
            cover.execute(api)
        return cover
