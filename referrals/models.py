from core.models import models, Currency, User, TimeStampedModel
from nexchange.settings import REFERRAL_CODE_LENGTH, REFERRAL_CODE_CHARS


class Program(TimeStampedModel):
    name = models.CharField(max_length=255)
    percent_first_degree = models.FloatField()
    percent_second_degree = models.FloatField()
    percent_third_degree = models.FloatField()
    currency = models.ManyToManyField(Currency)
    max_payout_btc = models.FloatField()


class ReferralCode(TimeStampedModel):
    code = models.CharField(max_length=10, unique=True)
    user = models.ForeignKey(User, related_name='referral_code')
    program = models.ForeignKey(Program, blank=True,
                                null=True, default=None)

    def save(self, *args, **kwargs):
        self.code = User.objects.make_random_password(
            length=REFERRAL_CODE_LENGTH,
            allowed_chars=REFERRAL_CODE_CHARS
        )
        super(ReferralCode, self).save(*args, **kwargs)


class Referral(TimeStampedModel):
    referrer = models.ForeignKey(User, related_name='referrer')
    referee = models.ForeignKey(User, related_name='referee')


class Balance(TimeStampedModel):
    user = models.ForeignKey(User)
    currency = models.ForeignKey(Currency)
    balance = models.FloatField(default=0)
