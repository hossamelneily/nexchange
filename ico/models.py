from core.common.models import TimeStampedModel
from core.validators import validate_eth
from core.models import Currency
from orders.models import Order
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist
from referrals.models import ReferralCode


class UtmSource(TimeStampedModel):
    name = models.CharField(max_length=255)
    comment = models.CharField(max_length=255, null=True, blank=True)
    referral_codes = models.ManyToManyField(ReferralCode, blank=True)

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):

    LOW = -5
    UNDEFINED = 0
    MEDIUM = 5
    HIGH = 10
    POTENTIAL_TYPES = (
        (UNDEFINED, _('UNDEFINED')),
        (LOW, _('LOW')),
        (MEDIUM, _('MEDIUM')),
        (HIGH, _('HIGH')),
    )
    email = models.EmailField(null=True, blank=True)
    sending_address = models.CharField(max_length=42, null=True,
                                       blank=True, validators=[validate_eth])
    user_comment = models.CharField(max_length=255, null=True, blank=True)
    admin_comment = models.CharField(max_length=255, null=True, blank=True)
    contribution = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    orders = models.ManyToManyField(Order, blank=True)
    is_passive = models.BooleanField(default=False)
    users = models.ManyToManyField(User, blank=True)
    eth_balance = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True, null=True,
                                      default=Decimal('0'))
    address_turnover = models.DecimalField(max_digits=18, decimal_places=8,
                                           blank=True, null=True,
                                           default=Decimal('0'),
                                           help_text='Converted to ETH')
    related_turnover = models.DecimalField(
        max_digits=18, decimal_places=8, blank=True, null=True,
        default=Decimal('0'),
        help_text='Turnover of all related orders. Must be equal or more than'
                  ' address_turnover. Converted to ETH.'
    )
    potential = models.IntegerField(
        choices=POTENTIAL_TYPES, default=UNDEFINED
    )
    utm_source = models.ForeignKey(UtmSource, blank=True, null=True)
    category = models.ManyToManyField(Category, blank=True)
    tokens_balance_eth = models.DecimalField(max_digits=18, decimal_places=8,
                                             blank=True, null=True,
                                             default=Decimal('0'))
    referral_code = models.ForeignKey(ReferralCode, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.tokens_balance_eth = self._tokens_balance_eth
        if self.referral_code and not self.utm_source:
            self.utm_source = self.referral_code.utmsource_set.last()
        super(Subscription, self).save(*args, **kwargs)

    @property
    def eth(self):
        return Currency.objects.get(code='ETH')

    @property
    def eth_currencies(self):
        return Currency.objects.filter(wallet=self.eth.wallet)

    @property
    def tokens(self):
        return self.eth_currencies.exclude(pk=self.eth.pk)

    def _get_token_balance_obj(self, token):
        try:
            balance = self.balance_set.filter(currency=token).latest('id')
            return balance
        except ObjectDoesNotExist:
            return None

    def _get_token_balance(self, token):
        obj = self._get_token_balance_obj(token)
        if obj:
            return obj.balance
        return Decimal('0')

    def _get_token_balance_eth(self, token):
        obj = self._get_token_balance_obj(token)
        if obj and obj.balance_eth:
            return obj.balance_eth
        return Decimal('0')

    @property
    def _tokens_balance_eth(self):
        total = Decimal('0')
        for token in self.tokens:
            total += self._get_token_balance_eth(token)
        return total

    @property
    def token_balances(self):
        res = {}
        for token in self.tokens:
            res.update({token.code: self._get_token_balance(token)})
        return res

    @property
    def non_zero_tokens(self):
        res = []
        for token, balance in self.token_balances.items():
            if balance > Decimal('0'):
                res.append(token)
        return res

    @property
    def tokens_count(self):
        return len(self.non_zero_tokens)

    @property
    def category_names(self):
        return [cat.name for cat in self.category.all()]

    def add_related_orders_and_users(self):
        if not self.sending_address:
            return
        # ETH is case insensitive
        orders = Order.objects.filter(
            withdraw_address__address__iexact=self.sending_address
        )

        for order in orders:
            self.orders.add(order)
            self.users.add(order.user)
        other_orders = Order.objects.filter(user__in=self.users.all()).exclude(
            id__in=orders
        )
        for order in other_orders:
            self.orders.add(order)

    def __str__(self):
        return "{} {}".format(self.email, self.sending_address)


class Balance(TimeStampedModel):

    subscription = models.ForeignKey(Subscription)
    currency = models.ForeignKey(Currency)
    balance = models.DecimalField(max_digits=18, decimal_places=8,
                                  blank=True, null=True,
                                  default=Decimal('0'))
    balance_eth = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True, null=True)
    address = models.CharField(max_length=42, null=True,
                               blank=True, validators=[validate_eth])

    def __str__(self):
        balance_str = str(self.balance).rstrip('0').rstrip('.')
        res = '{} {}'.format(balance_str, self.currency.code)
        if self.balance_eth:
            balance_eth_str = str(self.balance_eth).rstrip('0').rstrip('.')
            res = '{}({} ETH)'.format(res, balance_eth_str)

        return res
