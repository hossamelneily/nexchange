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
from nexchange.api_clients.bittrex import BittrexApiClient
from payments.utils import money_format
from audit_log.models import AuthStampedModel
from nexchange.api_clients.factory import ApiClientFactory


BITTREX_API = BittrexApiClient()
API_FACTORY = ApiClientFactory()


class Reserve(TimeStampedModel):
    currency = models.ForeignKey(Currency)
    is_limit_reserve = models.BooleanField(default=False)
    target_level = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    allowed_diff = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    maximum_level = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('0')
    )
    minimum_level = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('0')
    )
    minimum_main_account_level = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('0')
    )

    def __str__(self):
        return '{} reserve'.format(self.currency.code)

    def sum_account_field(self, field_name):
        accounts = self.account_set.filter(disabled=False)
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
    def min_expected_level(self):
        return self.target_level - self.allowed_diff

    @property
    def max_expected_level(self):
        return self.target_level + self.allowed_diff

    @property
    def has_target_level(self):
        if self.min_expected_level <= self.available <= self.max_expected_level:  # noqa
            return True
        return False

    @property
    def below_minimum_level(self):
        return self.available < self.minimum_level

    @property
    def over_maximum_level(self):
        return self.available > self.maximum_level

    @property
    def diff_from_target_level(self):
        return self.available - self.target_level

    @property
    def needed_trade_move(self):
        diff = self.diff_from_target_level
        trade_type = None
        if not self.has_target_level and self.is_limit_reserve:
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

    @property
    def all_reserves(self):
        return self.reservelog_set.all()

    @property
    def sell_reserves(self):
        return [r for r in self.all_reserves if r.needed_trade_type == 'SELL']

    @property
    def buy_reserves(self):
        return [r for r in self.all_reserves if r.needed_trade_type == 'BUY']

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

    @property
    def min_expected_level(self):
        return self.reserve.min_expected_level

    @property
    def max_expected_level(self):
        return self.reserve.max_expected_level

    @property
    def has_target_level(self):
        if self.min_expected_level <= self.available <= self.max_expected_level:  # noqa
            return True
        return False

    @property
    def below_minimum_level(self):
        return self.available < self.reserve.minimum_level

    @property
    def over_maximum_level(self):
        return self.available > self.reserve.maximum_level

    @property
    def diff_from_target_level(self):
        return self.available - self.reserve.target_level

    @property
    def diff_from_target_level_btc(self):
        return self.diff_from_target_level * self.rate_btc

    @property
    def needed_trade_type(self):
        diff = self.diff_from_target_level
        trade_type = None
        if not self.has_target_level:
            if diff > Decimal('0.0'):
                trade_type = 'SELL'
            else:
                trade_type = 'BUY'
        return trade_type

    @property
    def needed_trade_move(self):
        diff = self.diff_from_target_level
        trade_type = self.needed_trade_type
        return {'trade_type': trade_type, 'amount': abs(diff)}

    def __str__(self):
        return '{0}, diff: {1:.3f}'.format(self.reserve.currency.code,
                                           self.diff_from_target_level)


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
    disabled = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    healthy = models.BooleanField(default=False)

    @property
    def diff_from_required_reserve(self):
        return self.available - self.required_reserve

    def get_same_api_wallet(self, currency):
        try:
            return Account.objects.get(reserve__currency=currency,
                                       wallet=self.wallet)
        except Account.DoesNotExist:
            return

    def available_to_trade(self, currency=None):
        if currency is None:
            currency = self.reserve.currency
        account = self.get_same_api_wallet(currency)
        if not account or not self.trading_allowed:
            return Decimal('0')
        return account.available

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
        return '{} {} account'.format(self.reserve.currency.code,
                                      self.description)


class Cover(TimeStampedModel):

    BUY = 1
    SELL = 0
    COVER_TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )

    CANCELED = -1
    INITIAL = 1
    PRE_EXECUTED = 5
    EXECUTED = 9
    STATUS_TYPES = (
        (CANCELED, _('CANCELED')),
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
    reserves_cover = models.ForeignKey('risk_management.ReservesCover',
                                       blank=True, null=True)

    def recalculate(self):
        if not self.status == self.INITIAL:
            raise ValidationError(
                _('Cannot recalculate cover  in state {}').format(
                    self.get_status_display()
                )
            )
        if not self.account:
            raise ValidationError(_('Cannot recalculate cover which has '
                                    'no Account'))
        if not self.pair:
            raise ValidationError(_('Cannot recalculate cover which has '
                                    'no Pair'))
        _api = API_FACTORY.get_api_client(self.account.wallet)
        if self.cover_type == self.BUY:
            self.rate = _api.get_rate(self.pair, rate_type='Ask')
            self.amount_base = self.amount_quote / self.rate
        elif self.cover_type == self.SELL:
            self.rate = _api.get_rate(self.pair, rate_type='Bid')
            self.amount_quote = self.amount_base * self.rate
        self.save()

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
    def required_currency_amount_to_cover(self):
        if self.status == self.INITIAL and self.account:
            if self.cover_type == self.BUY:
                _currency = self.pair.quote
                _amount = self.amount_quote
            else:
                _currency = self.pair.base
                _amount = self.amount_base
            return _currency, _amount
        return None, Decimal('0')

    @property
    def missing_currency_amount_to_cover(self):
        _currency, _amount = self.required_currency_amount_to_cover
        if _currency:
            _available = self.account.available_to_trade(_currency)
            if _amount > _available:
                return _currency, _amount - _available

        return None, Decimal('0')

    @property
    def coverable(self):
        _currency, _amount = self.missing_currency_amount_to_cover
        if _currency:
            return False
        return True

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

    class Meta:
        ordering = ['-created_on']

    def get_defult_date_from():
        return now() - timedelta(hours=24)

    date_from = models.DateTimeField(
        blank=True, null=True, default=get_defult_date_from
    )
    date_to = models.DateTimeField(blank=True, null=True, default=now)
    days = models.DecimalField(max_digits=18, decimal_places=8,
                               default=Decimal('0'))

    def sum_pnls_field(self, field_name):
        reserve_logs = self.pnl_set.all()
        return Decimal(sum([getattr(log, field_name) for log in reserve_logs]))

    @property
    def period(self):
        return str(self.date_to - self.date_from)

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
    def non_null_pnls(self):
        return self.pnl_set.filter(pair__isnull=False).exclude(position=0)

    @property
    def positions(self):
        res = {}
        pnls = self.non_null_pnls
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
    def btc_pnls(self):
        return {pnl.pair.name: pnl.pnl_btc for pnl in self.non_null_pnls}

    @property
    def positions_str(self):
        positions = self.positions
        res = '|'
        for key, value in positions.items():
            res += ' {0:.1f} {1:s} |'.format(value, key)
        return res

    def save(self, *args, **kwargs):
        if self.days == Decimal('0'):
            self.days = \
                (self.date_to - self.date_from).total_seconds() / (3600 * 24)
        elif not self.pk:
            self.date_from = self.date_to - timedelta(days=self.days)

        create_pnls = False if self.pk else True
        res = super(PNLSheet, self).save(*args, **kwargs)
        if create_pnls:
            crypto = Currency.objects.filter(is_crypto=True).exclude(
                code__in=['RNS']).order_by('pk')
            codes = [curr.code for curr in crypto] + ['EUR', 'USD', 'GBP']
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

    class Meta:
        ordering = ['-created_on']

    def get_defult_date_from():
        return now() - timedelta(hours=24)

    pnl_sheet = models.ForeignKey(PNLSheet, null=True, blank=True)
    date_from = models.DateTimeField(
        blank=True, null=True, default=get_defult_date_from
    )
    date_to = models.DateTimeField(blank=True, null=True, default=now)
    days = models.DecimalField(max_digits=18, decimal_places=8,
                               default=Decimal('0'))
    pair = models.ForeignKey(Pair, blank=True, null=True)
    average_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                      default=Decimal('0'))
    volume_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                     default=Decimal('0'))
    base_volume_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                          default=Decimal('0'))
    average_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                      default=Decimal('0'))
    volume_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                     default=Decimal('0'))
    base_volume_bid = models.DecimalField(max_digits=18, decimal_places=8,
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
    position = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'))
    base_position = models.DecimalField(max_digits=18, decimal_places=8,
                                        default=Decimal('0'))
    realized_volume = models.DecimalField(max_digits=18, decimal_places=8,
                                          default=Decimal('0'))
    pnl_realized = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    pnl_unrealized = models.DecimalField(max_digits=18, decimal_places=8,
                                         default=Decimal('0'))
    pnl = models.DecimalField(max_digits=18, decimal_places=8,
                              default=Decimal('0'))
    pnl_btc = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))
    pnl_usd = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))
    pnl_eth = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))
    pnl_eur = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0'))

    @property
    def _position(self):
        return self.volume_ask - self.volume_bid

    @property
    def position_str(self):
        asset = '<asset>' if not self.pair else self.pair.quote.code
        return '{} {}'.format(self.position, asset)

    @property
    def _base_position(self):
        return self.base_volume_bid - self.base_volume_ask

    @property
    def base_position_str(self):
        currency = '<points>' if not self.pair else self.pair.base.code
        return '{} {}'.format(self.base_position, currency)

    @property
    def _realized_volume(self):
        return min([self.volume_ask, self.volume_bid])

    @property
    def _pnl_realized(self):
        return (self.average_bid - self.average_ask) * self._realized_volume

    @property
    def _pnl_unrealized(self):
        if self._position >= Decimal('0'):
            rate = self.average_ask
        else:
            rate = self.average_bid
        return (self.exit_price - rate) * self._position

    @property
    def _pnl(self):
        return self._pnl_realized + self._pnl_unrealized

    @property
    def pnl_str(self):
        currency = '<points>' if not self.pair else self.pair.base.code
        return '{} {}'.format(self.pnl, currency)

    @property
    def _pnl_btc(self):
        return self._pnl * self.rate_btc

    @property
    def _pnl_usd(self):
        return self._pnl * self.rate_usd

    @property
    def _pnl_eth(self):
        return self._pnl * self.rate_eth

    @property
    def _pnl_eur(self):
        return self._pnl * self.rate_eur

    @property
    def period(self):
        return str(self.date_to - self.date_from)

    def _set_pnl_parameters(self):
        filter = {
            'created_on__range': [self.date_from, self.date_to],
            'status': Order.COMPLETED
        }
        opposite_pair_name = '{}{}'.format(self.pair.quote.code,
                                           self.pair.base.code)
        cover_filter = {
            'created_on__range': [self.date_from, self.date_to],
            'status': Cover.EXECUTED,
            'pair__name__in': [self.pair.name, opposite_pair_name]
        }
        covers = Cover.objects.filter(**cover_filter)
        self.base_volume_ask = self.base_volume_bid = self.volume_ask = \
            self.volume_bid = Decimal('0')
        for cover in covers:
            if cover.pair == self.pair:
                if cover.cover_type == Cover.BUY:
                    self.volume_bid += cover.amount_quote
                    self.base_volume_bid += cover.amount_base
                if cover.cover_type == Cover.SELL:
                    self.volume_ask += cover.amount_quote
                    self.base_volume_ask += cover.amount_base
            else:
                if cover.cover_type == Cover.BUY:
                    self.volume_ask += cover.amount_base
                    self.base_volume_ask += cover.amount_quote
                if cover.cover_type == Cover.SELL:
                    self.volume_bid += cover.amount_base
                    self.base_volume_bid += cover.amount_quote
        ask_filter = deepcopy(filter)
        bid_filter = deepcopy(filter)
        ask_filter.update({'pair': self.pair})
        bid_filter.update({'pair__name': opposite_pair_name})
        ask_orders = Order.objects.filter(**ask_filter)
        self.pair_order_count = ask_orders.count()
        if self.pair_order_count:
            volumes_ask = ask_orders.aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            self.base_volume_ask += volumes_ask.get('amount_base__sum',
                                                    Decimal('0'))
            self.volume_ask += volumes_ask.get('amount_quote__sum',
                                               Decimal('0'))
        if self.base_volume_ask > Decimal('0'):
            self.average_ask = self.base_volume_ask / self.volume_ask

        bid_orders = Order.objects.filter(**bid_filter)
        self.opposite_pair_order_count = bid_orders.count()
        if self.opposite_pair_order_count:
            volumes_bid = bid_orders.aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            self.base_volume_bid += volumes_bid.get(
                'amount_quote__sum', Decimal('0')
            )
            self.volume_bid += volumes_bid.get(
                'amount_base__sum', Decimal('0')
            )

        if self.base_volume_bid > Decimal('0'):
            self.average_bid = self.base_volume_bid / self.volume_bid
        try:
            self.exit_price = Price.get_rate(self.pair.quote, self.pair.base)
        except Price.DoesNotExist:
            pass

    def _set_pnl_properties(self):
        props = {
            'position': self._position,
            'base_position': self._base_position,
            'realized_volume': self._realized_volume,
            'pnl_realized': self._pnl_realized,
            'pnl_unrealized': self._pnl_unrealized,
            'pnl': self._pnl,
            'pnl_usd': self._pnl_usd,
            'pnl_eth': self._pnl_eth,
            'pnl_eur': self._pnl_eur,
            'pnl_btc': self._pnl_btc
        }
        for field, prop in props.items():
            setattr(self, field, prop)

    def __str__(self):
        asset = '<asset>' if not self.pair else self.pair.quote.code
        currency = '<points>' if not self.pair else self.pair.base.code
        return 'position {} {} | P&l {} {}'.format(
            self.position, asset, self.pnl, currency)

    def save(self):
        if self.days == Decimal('0'):
            self.days = \
                (self.date_to - self.date_from).total_seconds() / (3600 * 24)
        elif not self.pk:
            self.date_from = self.date_to - timedelta(days=self.days)
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
        self._set_pnl_properties()
        super(PNL, self).save()

    @property
    def average_base_position_price(self):
        if self.base_position and self.position:
            return money_format(
                abs(self.position / self.base_position),
                places=8
            )

    @property
    def average_position_price(self):
        if self.base_position and self.position:
            return money_format(
                abs(self.base_position / self.position),
                places=8
            )


class DisabledCurrency(TimeStampedModel):
    currency = models.OneToOneField(Currency, unique=True,
                                    blank=False, null=False)
    disable_quote = models.BooleanField(default=True)
    disable_base = models.BooleanField(default=True)
    user_visible_reason = models.CharField(max_length=255, blank=True,
                                           null=True)
    admin_comment = models.CharField(max_length=255, blank=True, null=True)
    machine_comment = models.CharField(max_length=255, blank=True, null=True)


class ReservesCoverSettings(TimeStampedModel):

    currencies = models.ManyToManyField(Currency, related_name='currencies')
    default = models.BooleanField(default=False)
    coverable_part = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('1'),
        help_text='1 - 100%. Which part of required amount of reserve '
                  'difference from target_level to cover.'
    )

    @property
    def currencies_str(self):
        return ' '.join([c.code for c in self.currencies.all()])

    @property
    def coverable_str(self):
        return '{:.1f}%'.format(self.coverable_part * Decimal('100'))

    def save(self, *args, **kwargs):
        if self.coverable_part > Decimal('1'):
            raise ValidationError('Coverable Part Cannot be more than 1')
        super(ReservesCoverSettings, self).save(*args, **kwargs)

    def __str__(self):
        return '{}, {}'.format(self.currencies_str, self.coverable_str)


class ReservesCover(TimeStampedModel):

    settings = models.ForeignKey(ReservesCoverSettings, null=True, blank=True)
    portfolio_log = models.ForeignKey(PortfolioLog, blank=True)
    pair = models.ForeignKey(
        Pair,
        blank=True,
        null=True,
        help_text='Pair that is suggested to trade according to the reserve '
                  'levels.'
    )
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    amount_base = models.DecimalField(max_digits=18, decimal_places=8,
                                      default=Decimal('0'))
    pnl_sheets = models.ManyToManyField(PNLSheet)
    discard = models.BooleanField(default=False)
    comment = models.CharField(max_length=255, null=True, blank=True)

    def recalculate_covers(self):
        _covers = self.cover_set.filter(status=Cover.INITIAL)
        if not _covers:
            return
        _all_covers = self.cover_set.all()
        assert _covers.count() == _all_covers.count()
        for c in _covers:
            c.recalculate()
        _count = _covers.count()
        if _count == 2:
            _buy_cover = _covers.get(cover_type=Cover.BUY)
            _sell_cover = _covers.get(cover_type=Cover.SELL)
            self.amount_base = _buy_cover.amount_base
            self.amount_quote = _sell_cover.amount_base
        elif _count == 1:
            _cover = _covers.get()
            if _cover.cover_type == Cover.BUY:
                self.amount_base = _cover.amount_base
                self.amount_quote = _cover.amount_quote
            elif _cover.cover_type == Cover.SELL:
                self.amount_base = _cover.amount_quote
                self.amount_quote = _cover.amount_base
        self.save()

    def _get_suggested_trade(self):
        buy_reserves = {
            p.diff_from_target_level_btc: p
            for p in self.buy_reserves_filtered
        }
        sell_reserves = {
            p.diff_from_target_level_btc: p
            for p in self.sell_reserves_filtered
        }
        if not buy_reserves or not sell_reserves:
            return None, None, None
        min_buy = min(buy_reserves)
        max_sell = max(sell_reserves)
        base_log = buy_reserves[min_buy]
        quote_log = sell_reserves[max_sell]
        pair = Pair.objects.get(base=base_log.reserve.currency,
                                quote=quote_log.reserve.currency)
        abs_buy = abs(min_buy)
        abs_sell = abs(max_sell)
        amount_btc = abs_sell if abs_sell < abs_buy else abs_buy
        _amount_quote = \
            quote_log.diff_from_target_level * amount_btc / abs_sell
        _amount_base = abs(
            base_log.diff_from_target_level * amount_btc / abs_buy
        )
        coverable_part = self.settings.coverable_part
        amount_base = _amount_base * coverable_part
        amount_quote = _amount_quote * coverable_part
        return pair, amount_base, amount_quote

    def set_default_settings(self):
        # try except is to avoid adding fixtures
        try:
            settings = ReservesCoverSettings.objects.get(default=True)
        except ReservesCoverSettings.DoesNotExist:
            settings = ReservesCoverSettings.objects.create(default=True)
            settings.currencies.add(
                Currency.objects.get(code='BTC'),
                Currency.objects.get(code='XVG'),
                Currency.objects.get(code='DOGE'),
            )
        self.settings = settings

    def save(self, *args, **kwargs):
        if not self.pk and not self.settings:
            self.set_default_settings()
        if not self.pk and not self.portfolio_log_id:
            portfolio_log = PortfolioLog()
            portfolio_log.save()
            self.portfolio_log = portfolio_log
            _pair, _amount_base, _amount_quote = self._get_suggested_trade()
            if _pair and _amount_quote and _amount_base:
                self.pair, self.amount_quote, self.amount_base = \
                    _pair, _amount_quote, _amount_base
        is_new = True if not self.pk else False
        super(ReservesCover, self).save(*args, **kwargs)
        if is_new:
            self.create_cover_objects()
            self.set_default_pnl_sheets()

    def create_cover_objects(self):
        if not self.pair or not self.pk or self.cover_set.all():
            return
        suggested_pairs = BITTREX_API.get_api_pairs_for_pair(self.pair)
        reverse_pair = self.pair.reverse_pair
        if self.pair in suggested_pairs:
            cover = Cover()
            cover.cover_type = Cover.BUY
            cover.reserves_cover = self
            pair_data = suggested_pairs[self.pair]
            cover.currency = pair_data['main_currency']
            cover.account = Account.objects.get(
                description='Bittrex',
                reserve__currency=cover.currency
            )
            if cover.currency != self.pair.base:
                # just to skip if smth unexpected happens
                return
            cover.pair = self.pair
            cover.amount_base = self.amount_base
            cover.rate = BITTREX_API.get_rate(self.pair, rate_type='Ask')

            cover.amount_quote = cover.amount_base * cover.rate
            cover.save()
            self.amount_quote = cover.amount_quote
            self.save()
            return
        elif reverse_pair in suggested_pairs:
            _pair = reverse_pair
            cover = Cover()
            cover.cover_type = Cover.SELL
            cover.reserves_cover = self
            pair_data = suggested_pairs[_pair]
            cover.currency = pair_data['main_currency']
            cover.account = Account.objects.get(
                description='Bittrex',
                reserve__currency=cover.currency
            )
            if cover.currency != _pair.base:
                # just to skip if smth unexpected happens
                return
            cover.pair = _pair
            cover.amount_base = self.amount_quote
            cover.rate = BITTREX_API.get_rate(_pair, rate_type='Bid')

            cover.amount_quote = cover.amount_base * cover.rate
            cover.save()
            self.amount_base = cover.amount_quote
            self.save()
            return

        if 'BTC' in self.pair.name:
            return
        base_btc = Pair.objects.get(base=self.pair.base, quote__code='BTC')
        quote_btc = Pair.objects.get(base=self.pair.quote,
                                     quote__code='BTC')
        if quote_btc in suggested_pairs and base_btc in suggested_pairs:
            cover_base = Cover()
            cover_quote = Cover()
            cover_base.cover_type = Cover.BUY
            cover_quote.cover_type = Cover.SELL
            cover_base.reserves_cover = cover_quote.reserves_cover = self
            base_pair_data = suggested_pairs[base_btc]
            quote_pair_data = suggested_pairs[quote_btc]
            cover_base.currency = base_pair_data['main_currency']
            cover_quote.currency = quote_pair_data['main_currency']
            cover_base.account = Account.objects.get(
                description='Bittrex',
                reserve__currency=cover_base.currency
            )
            cover_quote.account = Account.objects.get(
                description='Bittrex',
                reserve__currency=cover_quote.currency
            )
            if cover_base.currency != base_btc.base or \
                    cover_quote.currency != quote_btc.base:
                # just to skip if smth unexpected happens
                return
            cover_base.pair = base_btc
            cover_quote.pair = quote_btc
            cover_quote.amount_base = self.amount_quote
            cover_base.rate = BITTREX_API.get_rate(base_btc, rate_type='Ask')
            cover_quote.rate = BITTREX_API.get_rate(quote_btc, rate_type='Bid')
            cover_quote.amount_quote = cover_base.amount_quote = \
                cover_quote.amount_base * cover_quote.rate
            cover_base.amount_base = cover_base.amount_quote / cover_base.rate
            cover_quote.save()
            cover_base.save()
            self.amount_base = cover_base.amount_base
            self.save()

    @property
    def rate(self):
        if self.amount_quote and self.amount_base:
            return money_format(
                abs(self.amount_base / self.amount_quote),
                places=8
            )

    @property
    def pnls(self):
        return PNL.objects.filter(
            pnl_sheet__in=self.pnl_sheets.all(),
            pair__in=[
                self.pair,
                getattr(self.pair, 'reverse_pair', None)
            ]
        )

    @property
    def pnl_rates(self):
        res = {}
        for pnl in self.pnls:
            res.update({
                int(pnl.pnl_sheet.days): {
                    'pair': pnl.pair.name,
                    'rate': pnl.average_position_price,
                    'base_rate': pnl.average_base_position_price,
                    'position': pnl.position,
                    'base_position': pnl.base_position
                }
            })
        return res

    @property
    def matched_pnl(self):
        for pnl in self.pnls.order_by('days'):
            if pnl.pair == self.pair:
                if pnl.position > self.amount_quote:
                    return pnl
            elif pnl.pair == self.pair.reverse_pair:
                if pnl.base_position > self.amount_quote:
                    return pnl

    @property
    def acquisition_rate(self):
        pnl = self.matched_pnl
        if pnl and self.pair:
            if pnl.pair == self.pair:
                return pnl.average_position_price
            elif pnl.pair == self.pair.reverse_pair:
                return pnl.average_base_position_price

    @property
    def static_rate_change(self):
        if self.acquisition_rate and self.rate:
            return money_format(
                (self.rate - self.acquisition_rate) / self.rate,
                places=8
            )

    @property
    def static_rate_change_str(self):
        if self.static_rate_change is not None:
            return '{0:.3f}%'.format(self.static_rate_change * Decimal(100))

    @property
    def sell_reserves(self):
        return self.portfolio_log.sell_reserves

    @property
    def sell_reserves_filtered(self):
        currencies = self.settings.currencies.all() if self.settings else []
        return [
            l for l in self.sell_reserves if l.reserve.currency in currencies
        ]

    @property
    def buy_reserves(self):
        return self.portfolio_log.buy_reserves

    @property
    def buy_reserves_filtered(self):
        currencies = self.settings.currencies.all() if self.settings else []
        return [
            l for l in self.buy_reserves if l.reserve.currency in currencies
        ]

    def get_last_pnl_sheet(self, days=1):
        try:
            return PNLSheet.objects.filter(days=days).latest('id')
        except PNLSheet.DoesNotExist:
            return

    def set_default_pnl_sheets(self):
        for days in [1, 7, 30]:
            sheet = self.get_last_pnl_sheet(days=days)
            if sheet:
                self.pnl_sheets.add(sheet)

    @property
    def first_cover(self):
        return self.cover_set.all().order_by('cover_type').first()


class PeriodicReservesCoverSettings(TimeStampedModel, AuthStampedModel):
    settings = models.ForeignKey(ReservesCoverSettings)
    current_reserves_cover = models.ForeignKey(ReservesCover, blank=True,
                                               null=True)
    minimum_rate_change = models.DecimalField(max_digits=18, decimal_places=8,
                                              default=Decimal('0.05'))

    @property
    def acceptable_rate(self):
        _change = getattr(self.current_reserves_cover, 'static_rate_change',
                          None)
        _min_change = self.minimum_rate_change
        if _change and _change >= _min_change:
            return True

    def str_minimum_rate_change(self):
        return ' {0:.3f}%'.format(self.minimum_rate_change * Decimal(100))
