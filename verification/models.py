from django.contrib.auth.models import User
from django.db import models
from verification.validators import validate_image_extension

from core.common.models import SoftDeletableModel, TimeStampedModel
from core.models import Currency
from payments.models import PaymentPreference
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


class VerificationTier(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    @property
    def trade_limits(self):
        return self.tradelimit_set.all()

    def __str__(self):
        return '{}: {}'.format(self.name, self.description)


class TradeLimit(TimeStampedModel):
    WITHDRAW = 'W'
    DEPOSIT = 'D'
    LIMIT_TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    FIAT = 'F'
    CRYPTO = 'C'
    TRADE_TYPES = (
        (FIAT, 'FIAT'),
        (CRYPTO, 'CRYPTO'),
    )
    limit_type = models.CharField(max_length=1, choices=LIMIT_TYPES)
    trade_type = models.CharField(max_length=1, choices=TRADE_TYPES)
    tier = models.ForeignKey(VerificationTier)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    days = models.IntegerField()
    currency = models.ForeignKey(Currency)

    def __str__(self):
        return _(
            '{trade_type}: {limit_type} {amount:.1f} {currency} per {days} '
            'days'
        ).format(
            trade_type=self.get_trade_type_display(),
            limit_type=self.get_limit_type_display(),
            amount=self.amount,
            currency=self.currency.code,
            days=self.days
        )


class Verification(TimeStampedModel, SoftDeletableModel):

    REJECTED = 'REJECTED'
    PENDING = 'PENDING'
    OK = 'OK'
    TYPES = (
        (REJECTED, 'Rejected'),
        (PENDING, 'Pending'),
        (OK, 'Approved'),
    )

    def _get_file_name(self, filename, root):
        if self.payment_preference and \
                self.payment_preference.provider_system_id:
            root1 = self.payment_preference.provider_system_id
        elif self.user:
            root1 = self.user.username
        else:
            root1 = 'all'
        root1 = ''.join(e for e in root1 if e.isalnum())
        return '/'.join([root1, root, filename])

    def identity_file_name(self, filename, root='verification/identity_docs'):
        return self._get_file_name(filename, root)

    def _utility_file_name(self, filename, root='verification/utility_docs'):
        return self._get_file_name(filename, root)

    user = models.ForeignKey(User, null=True, blank=True)
    payment_preference = models.ForeignKey(PaymentPreference, null=True,
                                           blank=True)
    identity_document = models.FileField(
        upload_to=identity_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    utility_document = models.FileField(
        upload_to=_utility_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    id_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                 blank=True, default=PENDING)
    util_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                   blank=True, default=PENDING)
    full_name = models.CharField(max_length=30, null=True, blank=True)
    note = models.CharField(max_length=30, null=True, blank=True)
    user_visible_comment = models.CharField(max_length=255,
                                            null=True, blank=True)
    user_input_comment = models.CharField(max_length=255,
                                          null=True, blank=True)

    def id_doc(self):
        if self.identity_document:
            link = '<a href="{}">"Download ID"</a>'.format(
                reverse('verification.download',
                        kwargs={'file_name': self.identity_document.name}),
            )
        else:
            link = '-'
        return link

    def residence_doc(self):
        if self.utility_document:
            link = '<a href="{}">"Download UTIL"</a>'.format(
                reverse('verification.download',
                        kwargs={'file_name': self.utility_document.name}),
            )
        else:
            link = '-'
        return link

    id_doc.allow_tags = True
    residence_doc.allow_tags = True

    def set_verification_tier_to_obj(self, obj):
        obj.refresh_from_db()
        if obj.is_verified:
            tier = VerificationTier.objects.get(name='Tier 1')
        else:
            tier = VerificationTier.objects.get(name='Tier 0')
        obj.tier = tier
        obj.save()

    def save(self):
        super(Verification, self).save()
        if self.payment_preference:
            self.set_verification_tier_to_obj(self.payment_preference)
