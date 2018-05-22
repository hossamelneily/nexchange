from django.contrib.auth.models import User
from django.db import models
from verification.validators import validate_image_extension

from core.common.models import SoftDeletableModel, TimeStampedModel
from core.models import Currency
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


class VerificationTier(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    level = models.IntegerField()
    upgrade_note = models.CharField(max_length=255, default='Contact Support')
    required_documents = models.ManyToManyField(
        'verification.DocumentType'
    )
    whitelisting_required = models.BooleanField(default=False)

    @classmethod
    def get_relevant_tier(cls, obj):
        # this is to support old verifications records which are approved by
        # util_status and id_status on verification object
        approved_types_legacy = []
        if obj.verification_set.filter(id_status=Verification.OK):
            approved_types_legacy.append(
                DocumentType.objects.get(name='ID')
            )
        if obj.verification_set.filter(util_status=Verification.OK):
            approved_types_legacy.append(
                DocumentType.objects.get(name='UTIL')
            )

        docs = VerificationDocument.objects.filter(
            verification__in=obj.verification_set.all(),
        )
        approved_docs = docs.filter(document_status=Verification.OK)
        approved_types = set(
            approved_types_legacy +
            [doc.document_type for doc in approved_docs]
        )
        approved_tiers = {tier.level: tier for tier in cls.objects.all()
                          if tier.check_tier_status(approved_types)}
        max_level = max(approved_tiers)
        return approved_tiers[max_level]

    def check_tier_status(self, approved_document_types):
        for doc_type in self.required_documents.all():
            if doc_type not in approved_document_types:
                return False
        return True

    @property
    def documents_to_upgrade(self):
        required_pks = [d.pk for d in self.required_documents.all()]
        try:
            next_tier = VerificationTier.objects.get(level=self.level + 1)
        except VerificationTier.DoesNotExist:
            return VerificationDocument.objects.none()
        return next_tier.required_documents.exclude(pk__in=required_pks)

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
    STATUSES = (
        (REJECTED, 'Rejected'),
        (PENDING, 'Pending'),
        (OK, 'Approved'),
    )
    STATUSES_TO_API = {
        OK: _('APPROVED'),
        PENDING: _('PENDING'),
        REJECTED: _('REJECTED'),
        None: _('UNDEFINED')
    }

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
    payment_preference = models.ForeignKey('payments.PaymentPreference',
                                           null=True, blank=True)
    identity_document = models.FileField(
        upload_to=identity_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    utility_document = models.FileField(
        upload_to=_utility_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    id_status = models.CharField(choices=STATUSES, max_length=10, null=True,
                                 blank=True, default=PENDING)
    util_status = models.CharField(choices=STATUSES, max_length=10, null=True,
                                   blank=True, default=PENDING)
    full_name = models.CharField(max_length=30, null=True, blank=False)
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
        tier = VerificationTier.get_relevant_tier(obj)
        obj.tier = tier
        obj.save()

    def _reject_if_no_document(self):
        if not self.utility_document and self.util_status == self.PENDING:
            self.util_status = self.REJECTED
        if not self.identity_document and self.id_status == self.PENDING:
            self.id_status = self.REJECTED

    def save(self):
        self._reject_if_no_document()
        super(Verification, self).save()
        if self.payment_preference:
            self.set_verification_tier_to_obj(self.payment_preference)

    @property
    def id_document_status(self):
        docs = self.verificationdocument_set.filter(
            document_type__name='ID'
        )
        statuses = [doc.document_status for doc in docs] + [self.id_status]
        for status in [self.OK, self.PENDING, self.REJECTED]:
            if status in statuses:
                return status

    @property
    def util_document_status(self):
        docs = self.verificationdocument_set.filter(
            document_type__name='UTIL'
        )
        statuses = [doc.document_status for doc in docs] + [self.util_status]
        for status in [self.OK, self.PENDING, self.REJECTED]:
            if status in statuses:
                return status

    def get_document_status(self, document_type_name):
        docs = self.verificationdocument_set.filter(
            document_type__name=document_type_name
        )
        if not docs:
            return
        statuses = [
            doc.document_status for doc in docs
        ]
        for status in [self.OK, self.PENDING, self.REJECTED]:
            if status in statuses:
                return status

    @property
    def id_is_approved(self):
        if self.id_status == self.OK:
            return True
        docs = self.verificationdocument_set.filter(
            document_type__name='ID'
        )
        for doc in docs:
            if doc.document_status == self.OK:
                return True
        return False

    @property
    def util_is_approved(self):
        if self.util_status == self.OK:
            return True
        docs = self.verificationdocument_set.filter(
            document_type__name='UTIL'
        )
        for doc in docs:
            if doc.document_status == self.OK:
                return True
        return False

    @property
    def approved_documents(self):
        return self.verificationdocument_set.filter(document_status=self.OK)

    @property
    def has_approved_documents(self):
        has_approved_docs = self.approved_documents.count() > 0
        return self.OK in [
            self.util_status, self.id_status
        ] or has_approved_docs

    @property
    def pending_documents(self):
        return self.verificationdocument_set.filter(
            document_status=self.PENDING
        )

    @property
    def has_pending_documents(self):
        has_pending_docs = self.pending_documents.count() > 0
        return self.PENDING in [
            self.util_status, self.id_status
        ] or has_pending_docs

    @property
    def has_bad_name(self):
        if not self.payment_preference \
                or not self.payment_preference.secondary_identifier:
            return False
        return self.full_name != self.payment_preference.secondary_identifier


class DocumentType(TimeStampedModel, SoftDeletableModel):

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    whitelisted_address_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class VerificationDocument(TimeStampedModel, SoftDeletableModel):

    REJECTED = Verification.REJECTED
    PENDING = Verification.PENDING
    OK = Verification.OK
    DOCUMENT_STATUSES = Verification.STATUSES

    def _get_file_name(self, filename):
        if self.document_type and self.document_type.name:
            root = 'kyc/{}'.format(self.document_type.name)
        else:
            root = 'kyc/all'
        if self.verification:
            root1 = str(self.verification.pk)
        else:
            root1 = 'all'
        return '/'.join([root1, root, filename])

    def document_file_name(self, filename):
        return self._get_file_name(filename)

    verification = models.ForeignKey(Verification)
    document_status = models.CharField(choices=DOCUMENT_STATUSES,
                                       max_length=10, null=True,
                                       blank=True, default=PENDING)
    document_type = models.ForeignKey(DocumentType)
    document_file = models.FileField(
        upload_to=document_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    whitelisted_address = models.ForeignKey('core.Address', null=True,
                                            blank=True, default=None)

    def download_document(self):
        if self.document_file:
            link = '<a href="{}">"Download {}"</a>'.format(
                reverse('verification.download',
                        kwargs={'file_name': self.document_file.name}),
                self.document_type.name
            )
        else:
            link = '-'
        return link

    download_document.allow_tags = True

    def __str__(self):
        return '{} {} {}'.format(self.document_type.name,
                                 self.verification.note, self.verification.pk)

    def save(self, *args, **kwargs):
        super(VerificationDocument, self).save(*args, **kwargs)
        if self.verification:
            self.verification.refresh_from_db()
            self.verification.save()
