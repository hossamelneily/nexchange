from django.db import models

from core.common.models import TimeStampedModel
from core.models import Currency, Pair
from ticker.models import Price
from orders.models import Order
from decimal import Decimal
from django.utils.translation import ugettext as _
from django_fsm import FSMIntegerField, transition
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.timezone import now, timedelta
from copy import deepcopy


class Reserve(TimeStampedModel):
    currency = models.ForeignKey(Currency)
    is_limit_reserve = models.BooleanField(default=False)
    expected_balance = models.DecimalField(max_digits=18, decimal_places=8,
                                           default=Decimal('0'))
    margin_balance = models.DecimalField(max_digits=18, decimal_places=8,
                                         default=Decimal('0'))

    def __str__(self):
        return '{} reserve'.format(self.currency.code)

    def sum_account_field(self, field_name):
        accounts = self.account_set.all()
        if accounts:
            res = accounts.aggregate(models.Sum(field_name))
            sum = res.get('{}__sum'.format(field_name))
        else:
            sum = Decimal('0.0')
        return sum

    @property
    def balance(self):
        return self.sum_account_field('balance')

    @property
    def pending(self):
        return self.sum_account_field('pending')

    @property
    def available(self):
        return self.sum_account_field('available')

    @property
    def min_expected_balance(self):
        return self.expected_balance - self.margin_balance

    @property
    def max_expected_balance(self):
        return self.expected_balance + self.margin_balance

    @property
    def has_expected_balance(self):
        if self.min_expected_balance <= self.balance <= self.max_expected_balance:  # noqa
            return True
        return False

    @property
    def diff_from_expected_balance(self):
        return self.balance - self.expected_balance

    @property
    def needed_trade_move(self):
        diff = self.diff_from_expected_balance
        trade_type = None
        if not self.has_expected_balance and self.is_limit_reserve:
            if diff > Decimal('0.0'):
                trade_type = 'SELL'
            else:
                trade_type = 'BUY'
        return {'trade_type': trade_type, 'amount': abs(diff)}

    @property
    def main_account(self):
        return self.account_set.get(is_main_account=True)


class PortfolioLog(TimeStampedModel):

    def save(self):
        log_reserves = False if self.pk else True
        res = super(PortfolioLog, self).save()
        if log_reserves:
            all_reserves = Reserve.objects.all()
            for reserve in all_reserves:
                reserve = ReserveLog(reserve=reserve, portfolio_log=self)
                reserve.save()
        return res

    def sum_reserve_logs_field(self, field_name):
        reserve_logs = self.reservelog_set.all()
        return Decimal(sum([getattr(log, field_name) for log in reserve_logs]))

    @property
    def total_btc(self):
        return self.sum_reserve_logs_field('available_btc')

    @property
    def total_usd(self):
        return self.sum_reserve_logs_field('available_usd')

    @property
    def total_eur(self):
        return self.sum_reserve_logs_field('available_eur')

    @property
    def total_eth(self):
        return self.sum_reserve_logs_field('available_eth')

    @property
    def assets_by_proportion(self):
        reserve_logs = self.reservelog_set.all()
        amount_btc = self.total_btc
        return {log.reserve.currency.code: log.available_btc / amount_btc for log in reserve_logs}  # noqa

    @property
    def assets_str(self):
        assets = self.assets_by_proportion
        res = '|'
        for key, value in assets.items():
            res += ' {0:.1f}% {1:s} |'.format(value * 100, key)
        return res

    def __str__(self):
        return '{}'.format(self.pk)


class ReserveLog(TimeStampedModel):
    reserve = models.ForeignKey(Reserve)
    portfolio_log = models.ForeignKey(PortfolioLog, null=True, blank=True)
    available = models.DecimalField(max_digits=18, decimal_places=8,
                                    default=Decimal('0'), blank=True)
    rate_btc = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_usd = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_eur = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_eth = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)

    def save(self):
        if not self.reserve:
            raise ValidationError('No reserve defined')
        if not self.pk:
            if not self.available:
                self.available = self.reserve.available
            reserve_currency = self.reserve.currency
            for quote_currency in ['BTC', 'USD', 'EUR', 'ETH']:
                field = 'rate_{}'.format(quote_currency.lower())
                if not getattr(self, field):
                    try:
                        rate = Price.get_rate(reserve_currency, quote_currency)
                        setattr(self, field, rate)
                    except Price.DoesNotExist:
                        continue
        super(ReserveLog, self).save()

    @property
    def available_btc(self):
        return self.available * self.rate_btc

    @property
    def available_usd(self):
        return self.available * self.rate_usd

    @property
    def available_eth(self):
        return self.available * self.rate_eth

    @property
    def available_eur(self):
        return self.available * self.rate_eur


class Account(TimeStampedModel):
    reserve = models.ForeignKey(Reserve)
    wallet = models.CharField(null=True, max_length=10,
                              blank=True, default=None)
    balance = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))
    available = models.DecimalField(max_digits=18, decimal_places=8,
                                    default=Decimal('0'))
    pending = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))
    required_reserve = models.DecimalField(max_digits=18, decimal_places=8,
                                           default=Decimal('0'))
    minimal_reserve = models.DecimalField(max_digits=18, decimal_places=8,
                                          default=Decimal('0'))
    trading_allowed = models.BooleanField(default=False)
    is_main_account = models.BooleanField(default=False)

    @property
    def diff_from_required_reserve(self):
        return self.available - self.required_reserve

    @property
    def diff_from_minimal_reserve(self):
        return self.available - self.minimal_reserve

    def save(self, *args, **kwargs):
        if self.is_main_account:
            old_mains = Account.objects.filter(is_main_account=True,
                                               reserve=self.reserve)
            for old_main in old_mains:
                if self != old_main:
                    old_main.is_main_account = False
                    old_main.save()
        super(Account, self).save(*args, **kwargs)

    def __str__(self):
        return '{} {} account'.format(self.reserve.currency.code, self.wallet)


class Cover(TimeStampedModel):

    BUY = 1
    SELL = 0
    COVER_TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )

    INITIAL = 1
    PRE_EXECUTED = 5
    EXECUTED = 9
    STATUS_TYPES = (
        (INITIAL, _('INITIAL')),
        (PRE_EXECUTED, _('PRE-EXECUTED')),
        (EXECUTED, _('EXECUTED')),
    )

    cover_type = models.IntegerField(
        choices=COVER_TYPES, default=BUY
    )
    pair = models.ForeignKey(Pair, null=True)
    currency = models.ForeignKey(Currency)
    orders = models.ManyToManyField(Order, related_name='covers')
    amount_base = models.DecimalField(max_digits=18, decimal_places=8)
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8,
                                       null=True)
    rate = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    cover_id = models.CharField(max_length=100, default=None,
                                null=True, blank=True, unique=True,
                                db_index=True)
    account = models.ForeignKey(Account, null=True)
    status = FSMIntegerField(choices=STATUS_TYPES, default=INITIAL)

    @transition(field=status, source=INITIAL, target=PRE_EXECUTED)
    def _pre_execute(self):
        pass

    def pre_execute(self):
        res = {'status': 'OK'}
        try:
            self._pre_execute()
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @transition(field=status, source=PRE_EXECUTED, target=EXECUTED)
    def _execute(self, api):
        if self.cover_type == self.BUY:
            trade_type = 'BUY'
        else:
            trade_type = 'SELL'
        res = api.trade_limit(self.pair, self.amount_base, trade_type,
                              rate=self.rate).get('result')
        if isinstance(res, dict):
            self.cover_id = res.get('uuid')
        else:
            raise ValidationError(
                'Cover is not covered, bad trace response: {}'.format(res)
            )

    def execute(self, api):
        res = {'status': 'OK'}
        try:
            self._execute(api)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @property
    def amount_to_main_account(self):
        account = self.account
        main_account = self.account.reserve.main_account
        available_to_send = account.diff_from_required_reserve
        max_to_send = account.diff_from_minimal_reserve
        need_to_send_additional = \
            self.amount_base - main_account.diff_from_required_reserve
        minimal_to_send_additional = \
            self.amount_base - main_account.diff_from_minimal_reserve
        if available_to_send >= need_to_send_additional:
            amount = need_to_send_additional
        elif available_to_send >= minimal_to_send_additional:
            amount = available_to_send
        elif max_to_send >= minimal_to_send_additional:
            amount = minimal_to_send_additional
        else:
            amount = max_to_send
        return amount


class PNLSheet(TimeStampedModel):

    def get_defult_date_from():
        return now() - timedelta(hours=24)

    date_from = models.DateTimeField(
        blank=True, null=True, default=get_defult_date_from
    )
    date_to = models.DateTimeField(blank=True, null=True, default=now)

    def sum_pnls_field(self, field_name):
        reserve_logs = self.pnl_set.all()
        return Decimal(sum([getattr(log, field_name) for log in reserve_logs]))

    @property
    def pnl_btc(self):
        return self.sum_pnls_field('pnl_btc')

    @property
    def pnl_usd(self):
        return self.sum_pnls_field('pnl_usd')

    @property
    def pnl_eur(self):
        return self.sum_pnls_field('pnl_eur')

    @property
    def pnl_eth(self):
        return self.sum_pnls_field('pnl_eth')

    @property
    def positions(self):
        res = {}
        pnls = self.pnl_set.filter(pair__isnull=False)
        for pnl in pnls:
            pnl_positions = {
                pnl.pair.base.code: pnl.base_position,
                pnl.pair.quote.code: pnl.position
            }
            for key, value in pnl_positions.items():
                if key in res:
                    res[key] += value
                else:
                    res.update({key: value})
        return res

    @property
    def positions_str(self):
        positions = self.positions
        res = '|'
        for key, value in positions.items():
            res += ' {0:.1f} {1:s} |'.format(value, key)
        return res

    def save(self):
        create_pnls = False if self.pk else True
        res = super(PNLSheet, self).save()
        if create_pnls:
            crypto = Currency.objects.filter(is_crypto=True).exclude(
                code__in=['RNS']).order_by('pk')
            codes = [curr.code for curr in crypto] + ['EUR', 'USD']
            names = []
            for i, code_base in enumerate(codes):
                for code_quote in codes[i + 1:]:
                    names.append('{}{}'.format(code_base, code_quote))
            pairs = Pair.objects.filter(name__in=names)
            for pair in pairs:
                pnl = PNL(pair=pair, pnl_sheet=self, date_from=self.date_from,
                          date_to=self.date_to)
                pnl.save()
        return res

    def __str__(self):
        return '{}'.format(self.pk)


class PNL(TimeStampedModel):

    def get_defult_date_from():
        return now() - timedelta(hours=24)

    pnl_sheet = models.ForeignKey(PNLSheet, null=True, blank=True)
    date_from = models.DateTimeField(
        blank=True, null=True, default=get_defult_date_from
    )
    date_to = models.DateTimeField(blank=True, null=True, default=now)
    pair = models.ForeignKey(Pair, blank=True, null=True)
    average_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                      default=Decimal('0'))
    volume_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                     default=Decimal('0'))
    average_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                      default=Decimal('0'))
    volume_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                     default=Decimal('0'))
    pair_order_count = models.IntegerField(null=True, blank=True)
    opposite_pair_order_count = models.IntegerField(null=True, blank=True)
    exit_price = models.DecimalField(max_digits=18, decimal_places=8,
                                     default=Decimal('0'))
    rate_btc = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_usd = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_eur = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)
    rate_eth = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'), blank=True)

    @property
    def position(self):
        return self.volume_ask - self.volume_bid

    @property
    def position_str(self):
        asset = '<asset>' if not self.pair else self.pair.quote.code
        return '{} {}'.format(self.position, asset)

    @property
    def base_position(self):
        return \
            self.volume_bid * self.average_bid - \
            self.volume_ask * self.average_ask

    @property
    def base_position_str(self):
        currency = '<points>' if not self.pair else self.pair.base.code
        return '{} {}'.format(self.base_position, currency)

    @property
    def realized_volume(self):
        return min([self.volume_ask, self.volume_bid])

    @property
    def pnl_realized(self):
        return (self.average_bid - self.average_ask) * self.realized_volume

    @property
    def pnl_unrealized(self):
        if self.position >= Decimal('0'):
            rate = self.average_ask
        else:
            rate = self.average_bid
        return (self.exit_price - rate) * self.position

    @property
    def pnl(self):
        return self.pnl_realized + self.pnl_unrealized

    @property
    def pnl_str(self):
        currency = '<points>' if not self.pair else self.pair.base.code
        return '{} {}'.format(self.pnl, currency)

    @property
    def pnl_btc(self):
        return self.pnl * self.rate_btc

    @property
    def pnl_usd(self):
        return self.pnl * self.rate_usd

    @property
    def pnl_eth(self):
        return self.pnl * self.rate_eth

    @property
    def pnl_eur(self):
        return self.pnl * self.rate_eur

    def _set_pnl_parameters(self):
        filter = {
            'created_on__range': [self.date_from, self.date_to],
            'status': Order.COMPLETED
        }
        ask_filter = deepcopy(filter)
        bid_filter = deepcopy(filter)
        ask_filter.update({'pair': self.pair})
        opposite_pair_name = '{}{}'.format(self.pair.quote.code,
                                           self.pair.base.code)
        bid_filter.update({'pair__name': opposite_pair_name})
        ask_orders = Order.objects.filter(**ask_filter)
        self.pair_order_count = ask_orders.count()
        if self.pair_order_count:
            volumes_ask = ask_orders.aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            base_volume = volumes_ask.get('amount_base__sum', Decimal('0'))
            self.volume_ask = volumes_ask.get('amount_quote__sum',
                                              Decimal('0'))
            self.average_ask = base_volume / self.volume_ask

        bid_orders = Order.objects.filter(**bid_filter)
        self.opposite_pair_order_count = bid_orders.count()
        if self.opposite_pair_order_count:
            volumes_bid = bid_orders.aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            quote_volume = volumes_bid.get('amount_quote__sum', Decimal('0'))
            self.volume_bid = volumes_bid.get('amount_base__sum', Decimal('0'))
            self.average_bid = quote_volume / self.volume_bid
        try:
            self.exit_price = Price.get_rate(self.pair.quote, self.pair.base)
        except Price.DoesNotExist:
            pass

    def __str__(self):
        asset = '<asset>' if not self.pair else self.pair.quote.code
        currency = '<points>' if not self.pair else self.pair.base.code

        return 'position {} {} | P&l {} {}'.format(
            self.position, asset, self.pnl, currency)

    def save(self):
        if all([self.date_from, self.date_to, self.pair, not self.pk]):
            self._set_pnl_parameters()
            base_currency = self.pair.base
            for quote_currency in ['BTC', 'USD', 'EUR', 'ETH']:
                field = 'rate_{}'.format(quote_currency.lower())
                if not getattr(self, field):
                    try:
                        rate = Price.get_rate(base_currency, quote_currency)
                        setattr(self, field, rate)
                    except Price.DoesNotExist:
                        continue

        super(PNL, self).save()
