from core.models import models, Currency, User, TimeStampedModel
from core.common.models import UniqueCodeModel, IpAwareModel
from nexchange.settings import REFERRAL_CODE_LENGTH, REFERRAL_CODE_CHARS
from django.db.models import Sum


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
            order_set

    @property
    def confirmed_orders_count(self):
        return self.orders.\
            filter(is_completed=True).count()

    @property
    def turnover(self):
        return self.referee.\
            order_set.filter(is_completed=True). \
            aggregate(Sum('amount_btc'))

    @property
    def program(self):
        return self.referrer.user. \
            referral_code.get(). \
            program

    @property
    def revenue(self,):
        return self.turnover / 100 * \
            self.program.percent_first_degree


class Balance(TimeStampedModel):
    user = models.ForeignKey(User)
    currency = models.ForeignKey(Currency)
    balance = models.FloatField(default=0)
