from django.db import models

from core.common.models import TimeStampedModel
from core.models import Currency, Pair
from orders.models import Order
from decimal import Decimal
from django.utils.translation import ugettext as _
from django_fsm import FSMIntegerField, transition
from django.core.exceptions import ValidationError


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
