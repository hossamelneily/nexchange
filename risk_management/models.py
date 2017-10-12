from django.db import models

from core.common.models import TimeStampedModel
from core.models import Currency
from decimal import Decimal


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
        res = self.account_set.all().aggregate(models.Sum(field_name))
        sum = res.get('{}__sum'.format(field_name))
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
        if not self.has_expected_balance:
            if diff > Decimal('0.0'):
                trade_type = 'SELL'
            else:
                trade_type = 'BUY'
        return {'trade_type': trade_type, 'amount': abs(diff)}


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
    trading_allowed = models.BooleanField(default=False)

    def __str__(self):
        return '{} {} account'.format(self.reserve.currency.code, self.wallet)
