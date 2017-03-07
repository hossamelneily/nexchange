from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils.crypto import get_random_string

from core.common.models import (IpAwareModel, TimeStampedModel,
                                UniqueFieldMixin)
from orders.models import Order
from django.conf import settings
from django.utils.translation import get_language, ugettext_lazy as _


class Program(TimeStampedModel):
    name = models.CharField(max_length=255)
    percent_first_degree = models.DecimalField(max_digits=18,
                                               decimal_places=8, default=0)
    percent_second_degree = models.DecimalField(max_digits=18,
                                                decimal_places=8, default=0)
    percent_third_degree = models.DecimalField(max_digits=18,
                                               decimal_places=8, default=0)
    currency = models.ManyToManyField('core.Currency')
    max_payout_btc = models.FloatField(default=-1)
    max_users = models.IntegerField(default=-1)
    max_lifespan = models.IntegerField(default=-1)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {}%->-{}%>->%{} in {} max " \
               "(users: {}, payout: {}, lifespan:{})"\
            .format(self.name, self.percent_first_degree * 100,
                    self.percent_second_degree * 100,
                    self.percent_third_degree * 100,
                    self.currency, self.max_users, self.max_payout_btc,
                    self.max_lifespan)


class ReferralCode(TimeStampedModel, UniqueFieldMixin):
    code = models.CharField(max_length=10, unique=True)
    link = models.CharField(max_length=255)
    user = models.ForeignKey(User, related_name='referral_code')
    program = models.ForeignKey(Program, blank=True,
                                null=True, default=None)

    def save(self, *args, **kwargs):
        self.code = self.gen_unique_value(
            lambda x: get_random_string(x),
            lambda x: ReferralCode.objects.filter(code=x).count(),
            settings.REFERRAL_CODE_LENGTH
        )

        if not self.program:
            self.program = Program.objects.first()

        if get_language() == 'ru':
            prefix = 'https://nexchange.ru/'
        else:
            prefix = 'https://nexchange.co.uk/'

        self.link = '{}?{}={}'.format(prefix, settings.REFERRER_GET_PARAMETER, self.code)

        super(ReferralCode, self).save(*args, **kwargs)

    def __str__(self):
        return "{} {} {}".format(self.code, self.user, self.program)


class Referral(IpAwareModel):
    def __init__(self, *args, **kwargs):
        super(Referral, self).__init__(*args, **kwargs)
        self.old_referral_revenue = 0
    # TODO: ensure that one user is not referred by many Users.
    code = models.ForeignKey('ReferralCode', default=None,
                             null=True)
    referee = models.ForeignKey(User, null=True, default=None,
                                related_name='referrals_set')

    @property
    def orders(self):
        if not self.referee:
            return None
        return self.referee. \
            orders.filter(status=Order.COMPLETED)

    @property
    def confirmed_orders_count(self):
        if not self.orders:
            return None
        return self.orders.count()

    @property
    def turnover(self):
        if not self.orders:
            return None
        res = self.\
            orders.aggregate(models.Sum('amount_base'))
        if res['amount_base__sum']:
            res = res['amount_base__sum']
        else:
            res = 0
        return round(res, 8)

    @property
    def program(self):
        return self.code.program

    @property
    def revenue(self,):
        # TODO: implement program and change to dynamic
        if not self.turnover:
            return 0

        res = Decimal(self.turnover) * \
            Decimal(self.program.percent_first_degree)
        return round(res, 8)

    def __str__(self):
        return "code: {} referee: {} orders: {} turnover: {} revenue: {} BTC"\
            .format(self.code, self.referee, self.orders,
                    self.turnover, self.revenue)
