from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from verification.validators import validate_image_extension

from core.common.models import SoftDeletableModel, TimeStampedModel, \
    FlagableMixin, NamedModel, RequestLog
from core.models import Currency, Country
from django.urls import reverse
from django.utils.translation import ugettext as _
from audit_log.models import AuthStampedModel
from django.utils.safestring import mark_safe
from nexchange.utils import get_nexchange_logger
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta
from django.utils import timezone

logger = get_nexchange_logger('Verification logger', with_email=True,
                              with_console=True)


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
    tier = models.ForeignKey(VerificationTier, on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    days = models.IntegerField()
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

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


class CategoryRule(TimeStampedModel, NamedModel):
    EQUAL = 0
    IN = 1
    RULE_TYPES = (
        (EQUAL, 'EQUAL'),
        (IN, 'IN'),
    )
    rule_type = models.IntegerField(choices=RULE_TYPES)
    key = models.CharField(
        max_length=127,
        help_text='Key of Verification payment preference payload'
    )
    value = models.CharField(
        max_length=127,
        help_text='Value of Verification payment preference payload'
    )


class VerificationCategory(TimeStampedModel, NamedModel):
    flagable = models.BooleanField(default=False)
    banks = models.ManyToManyField(
        'payments.Bank',
        help_text='This group will be add to Verification object if any of the'
                  ' banks from this list belogns to the payment_preferencce of'
                  ' that verification.',
        blank=True
    )
    rules = models.ManyToManyField(CategoryRule, blank=True)

    def __str__(self):
        res = super(VerificationCategory, self).__str__()
        if self.flagable:
            res = '!!! {} !!!'.format(res)
        return res


class Verification(TimeStampedModel, SoftDeletableModel, AuthStampedModel,
                   FlagableMixin):

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

    user = models.ForeignKey(User, null=True, blank=True,
                             on_delete=models.CASCADE)
    payment_preference = models.ForeignKey('payments.PaymentPreference',
                                           null=True, blank=True,
                                           on_delete=models.DO_NOTHING)
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
    full_name = models.CharField(max_length=127, null=True, blank=False)
    note = models.CharField(max_length=30, null=True, blank=True)
    user_visible_comment = models.CharField(max_length=255,
                                            null=True, blank=True)
    user_input_comment = models.CharField(max_length=255,
                                          null=True, blank=True)
    admin_comment = models.CharField(max_length=255,
                                     null=True, blank=True)
    category = models.ManyToManyField(VerificationCategory, blank=True)

    @mark_safe
    def id_doc(self):
        if self.identity_document:
            link = '<a href="/protected_media/{}">"ID Link"</a>'.format(
                self.identity_document.name
            )
        else:
            link = '-'
        return link

    @mark_safe
    def residence_doc(self):
        if self.utility_document:
            link = '<a href="/protected_media/{}">"UTIL Link"</a>'.format(
                self.utility_document.name
            )
        else:
            link = '-'
        return link

    def set_verification_tier_to_obj(self, obj):
        obj.refresh_from_db()
        _original_tier = obj.tier
        if _original_tier is None:
            _original_tier = VerificationTier.objects.get(name="Tier 0")
        tier = VerificationTier.get_relevant_tier(obj)
        obj.tier = tier
        obj.save()
        if obj.user_email is None:
            return
        if obj.tier.level > _original_tier.level:
            email_to = obj.user_email
            subject = 'Your user tier was upgraded!'
            message = 'Your tier was upgraded from {} to {}'.\
                format(_original_tier.name, obj.tier.name)
            obj.notify(email_to, subject, message)

    def _reject_if_no_document(self):
        if not self.utility_document and self.util_status == self.PENDING:
            self.util_status = self.REJECTED
        if not self.identity_document and self.id_status == self.PENDING:
            self.id_status = self.REJECTED

    def save(self, *args, **kwargs):
        self._reject_if_no_document()
        super(Verification, self).save(*args, **kwargs)
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

    @property
    def rejected_documents(self):
        rejected_docs = []
        for document_type in DocumentType.objects.all():
            status = self.get_document_status(document_type.name)
            if status == self.REJECTED:
                rejected_docs.append(document_type)
        return rejected_docs

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
        return not self.check_name(
            self.payment_preference.secondary_identifier
        )

    def _strip_name(self, name):
        return [
            n.lower() for n in name.split(' ') if n
        ] if isinstance(name, str) else name

    def _get_initials(self, name_list):
        return [n[0] for n in name_list]

    def check_name(self, name):
        expected_list = self._strip_name(name)
        full_list = self._strip_name(self.full_name)
        res = full_list == expected_list
        if not full_list or not expected_list:
            return res
        if not res and len(full_list) > len(expected_list):
            # middle name on verification
            res = \
                full_list[0] == expected_list[0] \
                and full_list[-1] == expected_list[-1]
        if not res and full_list[-1] == expected_list[-1]:
            # last name + initials
            res = self._get_initials(full_list) == self._get_initials(
                expected_list
            )

        return res

    @property
    def related_orders(self):
        if self.payment_preference:
            return self.payment_preference.payment_orders
        return []

    @property
    def referred_with(self):
        return [o.referred_with for o in self.related_orders]


class DocumentType(TimeStampedModel, SoftDeletableModel):

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    whitelisted_address_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class VerificationDocument(TimeStampedModel, SoftDeletableModel,
                           AuthStampedModel):

    REJECTED = Verification.REJECTED
    PENDING = Verification.PENDING
    OK = Verification.OK
    DOCUMENT_STATUSES = Verification.STATUSES

    def __init__(self, *args, **kwargs):
        super(VerificationDocument, self).__init__(*args, **kwargs)
        self.original_document_status = self.document_status if \
            self.document_status is not None else self.PENDING

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

    @mark_safe
    def image_tag(self):
        return '<embed src="/protected_media/{}" />'.format(
            self.document_file.name
        )

    image_tag.short_description = 'Image'

    def document_file_name(self, filename):
        return self._get_file_name(filename)

    verification = models.ForeignKey(Verification,
                                     on_delete=models.DO_NOTHING)
    document_status = models.CharField(choices=DOCUMENT_STATUSES,
                                       max_length=10, null=True,
                                       blank=True, default=PENDING)
    document_type = models.ForeignKey(DocumentType,
                                      on_delete=models.DO_NOTHING)
    document_file = models.FileField(
        upload_to=document_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    whitelisted_address = models.ForeignKey('core.Address', null=True,
                                            blank=True, default=None,
                                            on_delete=models.DO_NOTHING)
    admin_comment = models.CharField(max_length=255,
                                     null=True, blank=True)
    kyc_push = models.OneToOneField('verification.KycPushRequest', null=True,
                                    blank=True, default=None,
                                    on_delete=models.DO_NOTHING)

    @mark_safe
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

    def __str__(self):
        return '{} {} {}'.format(self.document_type.name,
                                 self.verification.note, self.verification.pk)

    def save(self, *args, **kwargs):
        if not self.pk and self.kyc_push:
            self.document_status = self.kyc_push.document_status
        super(VerificationDocument, self).save(*args, **kwargs)
        if self.verification:
            self.verification.refresh_from_db()
            self.verification.save()


class KycPushRequest(RequestLog):
    REJECTED = Verification.REJECTED
    PENDING = Verification.PENDING
    OK = Verification.OK

    identification_status = models.CharField(max_length=127, null=True,
                                             blank=True)
    identification_approved = models.BooleanField(default=False)
    valid_link = models.BooleanField(default=False)
    full_name = models.CharField(max_length=127, null=True, blank=True)
    nationality = models.ForeignKey(Country, null=True, blank=True,
                                    on_delete=models.DO_NOTHING,
                                    related_name='nationalities',)
    issuing_country = models.ForeignKey(Country, null=True, blank=True,
                                        on_delete=models.DO_NOTHING,
                                        related_name='issuing_countries')
    selected_country = models.ForeignKey(Country, null=True, blank=True,
                                         on_delete=models.DO_NOTHING,
                                         related_name='selected_countries')
    birth_date = models.DateField(blank=True, null=True)
    doc_expiration = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk or kwargs.pop('reload_from_payload', False):
            payload = self.get_payload_dict()
            first_name = payload.get('idFirstName')
            last_name = payload.get('idLastName')
            self.full_name = '{} {}'.format(first_name, last_name)
            self.birth_date = payload.get('idDob')
            self.doc_expiration = payload.get('idExpiry')
            self.identification_status = payload.get('identificationStatus')
            self.identification_approved = \
                self.identification_status == 'APPROVED'
            doc_data = payload.get('data', {})
            for api_key, db_key in {'docNationality': 'nationality',
                                    'docIssuingCountry': 'issuing_country',
                                    'selectedCountry': 'selected_country'}\
                    .items():
                value = doc_data.get(api_key)
                if not value:
                    continue
                try:
                    value_obj = Country.objects.get(country=value)
                except ObjectDoesNotExist:
                    continue
                setattr(self, db_key, value_obj)
        super(KycPushRequest, self).save(*args, **kwargs)

    @property
    def document_status(self):
        ok_push = self.identification_approved and self.valid_link
        return self.OK if ok_push else self.REJECTED

    def __str__(self):
        res = '{} {}'.format(self.full_name, self.birth_date)
        if self.issuing_country:
            res += ' {}'.format(self.issuing_country)
        res += ' {} {} {}'.format(
            self.identification_status, self.identification_approved,
            self.valid_link
        )
        return res


class IdentityToken(TimeStampedModel):
    token = models.CharField(max_length=255)
    order = models.ForeignKey('orders.Order', null=True, blank=True,
                              on_delete=models.DO_NOTHING)
    used = models.BooleanField(default=False)

    @property
    def expires(self):
        return self.created_on + timedelta(
            seconds=settings.IDENFY_TOKEN_EXPIRY_TIME
        )

    @property
    def expired(self):
        return (timezone.now() > self.expires)
