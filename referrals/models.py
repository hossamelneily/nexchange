from core.models import models, Currency, User, TimeStampedModel
from core.common.models import UniqueCodeModel, IpAwareModel
from nexchange.settings import REFERRAL_CODE_LENGTH, REFERRAL_CODE_CHARS, \
    REFERRAL_FEE
from django.db.models import Sum
from decimal import Decimal


class Program(TimeStampedModel):
    name = models.CharField(max_length=255)
    percent_first_degree = models.FloatField()
    percent_second_degree = models.FloatField(default=0)
    percent_third_degree = models.FloatField(default=0)
    currency = models.ManyToManyField(Currency)
    max_payout_btc = models.FloatField(default=-1)
    max_users = models.IntegerField(default=-1)


class ReferralCode(TimeStampedModel, UniqueCodeModel):
    code = models.CharField(max_length=10, unique=True)
    user = models.ForeignKey(User, related_name='referral_code')
    program = models.ForeignKey(Program, blank=True,
                                null=True, default=None)

    def save(self, *args, **kwargs):
        self.code = self.get_random_code(REFERRAL_CODE_CHARS,
                                         REFERRAL_CODE_LENGTH)

        super(ReferralCode, self).save(*args, **kwargs)


class Referral(IpAwareModel):
    code = models.ForeignKey(ReferralCode, default=None,
                             null=True)
    referee = models.ForeignKey(User, null=True, default=None,
                                related_name='referee')

    @property
    def orders(self):
        return self.referee. \
            orders.filter(is_completed=True)

    @property
    def confirmed_orders_count(self):
        return self.orders.count()

    @property
    def turnover(self):
        res = self.\
            orders.aggregate(Sum('amount_btc'))
        return res['amount_btc__sum']

    @property
    def program(self):
        return self.referrer.user. \
            referral_code.get(). \
            program

    @property
    def revenue(self,):
        # TODO: implement program and change to dynamic
        return Decimal(self.turnover) / 100 * \
            REFERRAL_FEE


class Balance(TimeStampedModel):
    user = models.ForeignKey(User)
    currency = models.ForeignKey(Currency)
    balance = models.FloatField(default=0)
