from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import JSONField

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from decimal import Decimal
from core.common.models import SoftDeletableModel, \
    TimeStampedModel, FlagableMixin, IpAwareModel, NamedModel
from ticker.models import Price
from django.utils.timezone import now, timedelta
from core.models import Location, Country, BtcBase, Currency
from verification.models import VerificationDocument
import requests
import json


class PaymentMethodManager(models.Manager):

    def get_by_natural_key(self, bin_code):
        return self.get(bin=bin_code)


DEFAULT_FEE_CURRENCY_PK = 4  # USD


class PaymentMethod(TimeStampedModel, SoftDeletableModel):
    NATURAL_KEY = 'bin'

    CUSTOMER = 0
    MERCHANT = 1

    USERS = (
        (CUSTOMER, 'CUSTOMER'),
        (MERCHANT, 'MERCHANT'),
    )

    MANUAL = 0
    AUTO = 1
    MANUAL_AND_AUTO = 2
    ON_ORDER_SUCCESS_MODAL = 3
    CHECKOUT_TYPES = (
        (MANUAL, 'MANUAL'),
        (AUTO, 'AUTO'),
        (MANUAL_AND_AUTO, 'MANUAL & AUTO'),
        (ON_ORDER_SUCCESS_MODAL, 'Checkout on Order Success'),
    )

    METHODS_NAMES_WITH_BANK_DETAILS = ['SEPA', 'SWIFT']
    BIN_LENGTH = 6
    objects = PaymentMethodManager()
    name = models.CharField(max_length=100)
    handler = models.CharField(max_length=100, null=True)
    bin = models.IntegerField(null=True, default=None)
    fee_deposit = models.DecimalField(max_digits=5, decimal_places=3,
                                      null=True, blank=True, default=0)
    fee_withdraw = models.DecimalField(max_digits=5, decimal_places=3,
                                       null=True, blank=True, default=0)
    is_slow = models.BooleanField(default=False)
    payment_window = models
    is_internal = models.BooleanField(default=False)
    pays_withdraw_fee = models.IntegerField(
        choices=USERS, default=MERCHANT
    )
    pays_deposit_fee = models.IntegerField(
        choices=USERS, default=CUSTOMER
    )
    allowed_amount_unpaid = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.01,
        help_text='Allowed difference between order amount (ticker_amount) '
                  'and payment amount (amount_cash).'
    )
    checkout_type = models.IntegerField(
        choices=CHECKOUT_TYPES, default=MANUAL
    )
    required_verification_buy = models.BooleanField(default=False)
    allowed_countries = models.ManyToManyField(
        Country,
        help_text='Specifies the countires for which this payment method is '
                  'allowed. If there is no countries specified then it is '
                  'allowed for all of them')
    minimal_fee_amount = models.DecimalField(max_digits=5, decimal_places=2,
                                             null=True, blank=True, default=3)
    minimal_fee_currency = models.ForeignKey(Currency,
                                             default=DEFAULT_FEE_CURRENCY_PK,
                                             on_delete=models.DO_NOTHING)

    @property
    def auto_checkout(self):
        if self.checkout_type in [self.AUTO, self.MANUAL_AND_AUTO]:
            return True
        return False

    @property
    def manual_checkout(self):
        if self.checkout_type in [self.MANUAL, self.MANUAL_AND_AUTO]:
            return True
        return False

    @property
    def on_order_success_modal_checkout(self):
        if self.checkout_type in [self.ON_ORDER_SUCCESS_MODAL]:
            return True
        return False

    def natural_key(self):
        return self.bin

    def __str__(self):
        return "{} ({})".format(self.name, self.bin)


class PaymentPreference(TimeStampedModel, SoftDeletableModel, FlagableMixin):
    class Meta:
        unique_together = ('user', 'identifier', 'payment_method')
    # NULL or Admin for out own (buy adds)
    buy_enabled = models.BooleanField(default=True)
    sell_enabled = models.BooleanField(default=True)
    user = models.ForeignKey(User, default=None, blank=True, null=True,
                             on_delete=models.CASCADE)
    payment_method = models.ForeignKey('PaymentMethod', default=None,
                                       on_delete=models.DO_NOTHING)
    currency = models.ManyToManyField('core.Currency')
    provider_system_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )
    # Optional, sometimes we need this to confirm
    identifier = models.CharField(max_length=100, blank=True, null=True)
    secondary_identifier = models.CharField(max_length=100,
                                            default=None,
                                            null=True,
                                            blank=True)
    comment = models.CharField(max_length=255, default=None,
                               blank=True, null=True)
    name = models.CharField(max_length=100, null=True,
                            blank=True, default=None)
    beneficiary = models.CharField(max_length=100, null=True,
                                   blank=True, default=None)
    bic = models.CharField(max_length=100, null=True,
                           blank=True, default=None)
    ccexp = models.CharField(max_length=5, null=True, blank=True, default=None)
    cvv = models.CharField(max_length=4, null=True, blank=True, default=None)
    physical_address_bank = models.CharField(max_length=255, null=True,
                                             blank=True, default=None)
    # If exists, overrides the address save in the profile of the owner
    physical_address_owner = models.CharField(max_length=255, null=True,
                                              blank=True, default=None)
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.DO_NOTHING)
    tier = models.ForeignKey('verification.VerificationTier', blank=True,
                             null=True, on_delete=models.DO_NOTHING)
    is_immediate_payment = models.BooleanField(
        default=False,
        help_text='This should be moved to PaymentMethod when methods will '
                  'be created automatically on Safe Charge PushRequests.'
    )
    push_request = models.ForeignKey('payments.PushRequest', blank=True,
                                     null=True, on_delete=models.DO_NOTHING)
    bank_bin = models.ForeignKey('payments.BankBin', null=True, blank=True,
                                 on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        if not hasattr(self, 'payment_method'):
            self.payment_method = self.guess_payment_method()
        super(PaymentPreference, self).save(*args, **kwargs)

    def guess_payment_method(self):
        identifier = ''.join(self.identifier.split(' '))
        card_bin = identifier[:PaymentMethod.BIN_LENGTH]
        payment_method = []
        while all([identifier,
                   not len(payment_method),
                   len(card_bin) > 0]):
            payment_method = PaymentMethod.objects.filter(bin=card_bin)
            card_bin = card_bin[:-1]

        return payment_method[0] if len(payment_method) \
            else PaymentMethod.objects.get(name='Cash')

    @property
    def user_verified_for_buy(self):
        required_verification = self.payment_method.\
            required_verification_buy
        if not required_verification:
            return True
        if not self.user.profile.is_verified:
            return False
        return True

    def _get_id_document_status(self, verifications=None):
        if verifications is None:
            verifications = self.verification_set.all()
        if not verifications:
            return
        model = verifications.model
        statuses = [
            v.id_document_status for v in verifications
        ]
        for status in [model.OK, model.PENDING, model.REJECTED]:
            if status in statuses:
                return status

    def id_document_status(self):
        return self._get_id_document_status()

    def _get_utility_document_status(self, verifications=None):
        if verifications is None:
            verifications = self.verification_set.all()
        if not verifications:
            return
        model = verifications.model
        statuses = [
            v.util_document_status for v in verifications
        ]
        for status in [model.OK, model.PENDING, model.REJECTED]:
            if status in statuses:
                return status

    @property
    def residence_document_status(self):
        return self._get_utility_document_status()

    @property
    def util_document_status(self):
        return self._get_utility_document_status()

    def get_payment_preference_document_status(self, document_type_name,
                                               verifications=None):
        if verifications is None:
            verifications = self.verification_set.all()
        prop_name = '_get_{}_document_status'.format(
            document_type_name.lower()
        )
        if hasattr(self, prop_name):
            return getattr(self, prop_name)(verifications=verifications)
        if not verifications:
            return
        model = verifications.model
        statuses = [
            v.get_document_status(document_type_name) for v in verifications
        ]
        for status in [model.OK, model.PENDING, model.REJECTED]:
            if status in statuses:
                return status

    @property
    def is_verified(self):
        verifications = self.verification_set.all()
        id_status = False
        util_status = False
        for ver in verifications:
            if ver.id_is_approved:
                id_status = True
            if ver.util_is_approved:
                util_status = True
            if id_status and util_status:
                return True
        return False

    @property
    def successful_payments(self):
        return self.payment_set.filter(is_success=True)

    def get_successful_payments_amount(self, currency=None, days=None):
        if not currency:
            currency = Currency.objects.get(code='USD')
        if days:
            relevant = now() - timedelta(days=days)
            payments = self.successful_payments.filter(
                created_on__gte=relevant
            )
        else:
            payments = self.successful_payments
        total_amount = Decimal('0')
        for payment in payments:
            total_amount += Price.convert_amount(
                payment.amount_cash, payment.currency,
                currency)
        return total_amount

    @property
    def total_payments_usd(self):
        return self.get_successful_payments_amount()

    @property
    def trade_limits_info(self):
        info = {}
        limits_info = []
        if not self.tier:
            return info
        limits = self.tier.trade_limits.all()
        for limit in limits:
            total_amount = self.get_successful_payments_amount(
                days=limit.days, currency=limit.currency
            )
            msg = \
                '{total:.2f} {currency} out of allowed {limit_amount:.2f} ' \
                '{currency} per {days} day{plural}'.format(
                    total=total_amount,
                    currency=limit.currency,
                    limit_amount=limit.amount,
                    days=limit.days,
                    plural='s' if limit.days > 1 else ''
                )
            out_of_limit = total_amount > limit.amount
            limits_info.append({
                'message': msg,
                'out_of_limit': out_of_limit,
                'days': limit.days,
                'amount': limit.amount,
                'currency': limit.currency.code,
                'total_amount': total_amount,
            })
        info['trade_limits'] = limits_info
        info['tier'] = {
            'name': self.tier.name,
            'upgrade_note': self.tier.upgrade_note,
            'upgrade_documents': [
                d.api_key for d in self.tier.documents_to_upgrade
            ]
        }
        return info

    @property
    def out_of_limit(self):
        if not self.tier:
            return True
        limits = self.tier.trade_limits.all()
        for limit in limits:
            total_amount = self.get_successful_payments_amount(
                days=limit.days, currency=limit.currency
            )
            if total_amount > limit.amount:
                return True
        return False

    @property
    def verification_documents(self):
        return VerificationDocument.objects.filter(
            verification__in=self.verification_set.all()
        )

    @property
    def whitelisted_addresses(self):
        whitelist_docs = self.verification_documents.filter(
            document_type__whitelisted_address_required=True,
            document_status=VerificationDocument.OK
        )
        _addresses = [
            doc.whitelisted_address
            for doc in whitelist_docs if doc.whitelisted_address
        ]
        return _addresses

    @property
    def whitelisted_addresses_info(self):
        res = {}
        _docs = self.verification_documents.filter(
            document_type__whitelisted_address_required=True
        )
        model = _docs.model
        _addresses = [
            doc.whitelisted_address
            for doc in _docs if doc.whitelisted_address
        ]
        for _address in _addresses:
            statuses = [
                d.document_status for d in _docs.filter(
                    whitelisted_address=_address
                )
            ]
            for status in [model.OK, model.PENDING, model.REJECTED]:
                if status in statuses:
                    res.update({_address: status})
                    break
        return res

    @property
    def approved_verifications(self):
        vers = self.verification_set.all()
        return [v for v in vers if v.has_approved_documents]

    @property
    def bad_name_verifications(self):
        return [
            v for v in self.approved_verifications
            if v.has_bad_name
        ]

    @property
    def name_on_card_matches(self):
        # Approve if we dont have secondary_identifier (name)
        if not self.secondary_identifier:
            return True
        vers = self.approved_verifications
        for v in vers:
            if not v.check_name(self.secondary_identifier):
                return False
        return True

    def __str__(self):
        return "{} {}".format(self.payment_method.name,
                              self.identifier)


class Payment(BtcBase, SoftDeletableModel, FlagableMixin):
    nonce = models.CharField(_('Nonce'),
                             max_length=256,
                             null=True,
                             blank=True)
    amount_cash = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey('core.Currency', default=None,
                                 on_delete=models.DO_NOTHING)
    is_redeemed = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    payment_preference = models.ForeignKey('PaymentPreference',
                                           null=False, default=None,
                                           on_delete=models.DO_NOTHING)
    # Super admin if we are paying for BTC
    user = models.ForeignKey(User, default=None, null=True, blank=True,
                             on_delete=models.DO_NOTHING)
    # Todo consider one to many for split payments, consider order field on
    # payment
    order = models.ForeignKey('orders.Order', null=True, default=None,
                              on_delete=models.DO_NOTHING)
    reference = models.CharField(max_length=255,
                                 null=True, default=None)
    comment = models.CharField(max_length=255,
                               null=True, default=None)
    payment_system_id = models.CharField(max_length=255, unique=True,
                                         null=True, default=None)
    secondary_payment_system_id = models.CharField(max_length=255, unique=True,
                                                   null=True, default=None)
    auth_code = models.CharField(max_length=50, blank=True,
                                 null=True, default=None)

    @property
    def api_time(self):
        safe_time = self.created_on - settings.PAYMENT_WINDOW_SAFETY_INTERVAL
        return safe_time.__format__('%Y-%m-%d %H:%M:%S')

    @property
    def api_time_iso_8601(self):
        safe_time = self.created_on - settings.PAYMENT_WINDOW_SAFETY_INTERVAL
        return safe_time.__format__('%Y-%m-%dT%H:%M:%S+00:00')

    def __str__(self):
        return '{} {} - {}'.format(self.amount_cash,
                                   self.currency,
                                   self.payment_preference)

    @property
    def kyc_refund_time(self):
        return self.created_on + settings.KYC_WAIT_REFUND_INTERVAL

    @property
    def kyc_void_time(self):
        return self.created_on + settings.KYC_WAIT_VOID_INTERVAL

    @property
    def kyc_wait_refund_period_expired(self):
        due_date_passed = now() > self.kyc_refund_time
        kyc_sent = \
            self.payment_preference \
            and self.payment_preference.verification_set.count()
        user_email = self.user and self.user.email
        return due_date_passed and not kyc_sent and not user_email

    @property
    def kyc_wait_void_period_expired(self):
        due_date_passed = now() > self.kyc_void_time
        kyc_sent = \
            self.payment_preference \
            and self.payment_preference.verification_set.count()
        return due_date_passed and not kyc_sent


class PaymentCredentials(TimeStampedModel, SoftDeletableModel):
    payment_preference = models.ForeignKey('PaymentPreference',
                                           on_delete=models.DO_NOTHING)
    uni = models.CharField(_('Uni'), max_length=60,
                           null=True, blank=True)
    nonce = models.CharField(_('Nonce'), max_length=256,
                             null=True, blank=True)
    token = models.CharField(_('Token'), max_length=256,
                             null=True, blank=True)
    is_default = models.BooleanField(_('Default'), default=False)
    is_delete = models.BooleanField(_('Delete'), default=False)

    def __str__(self):
        pref = self.paymentpreference_set.get()
        return "{0} - ({1})".format(pref.user.username,
                                    pref.identifier)


class RequestLog(IpAwareModel):

    class Meta:
        abstract = True

    url = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    payload = models.TextField(null=True, blank=True)
    payload_json = JSONField(null=True, blank=True)


class FailedRequest(RequestLog):
    validation_error = models.TextField(null=True, blank=True)
    order = models.ForeignKey('orders.Order',
                              on_delete=models.CASCADE)


class PushRequest(RequestLog):
    payment = models.ForeignKey(Payment, blank=True, null=True,
                                on_delete=models.CASCADE)
    valid_checksum = models.BooleanField(default=False)
    valid_timestamp = models.BooleanField(default=False)
    valid_ip = models.BooleanField(default=False)
    payment_created = models.BooleanField(
        default=False,
        help_text='It is possible to get more than one PushRequest for one '
                  'payment. If this is True - payment was created with this '
                  'PushRequest.'
    )

    @property
    def is_valid(self):
        return all([self.valid_checksum, self.valid_timestamp, self.valid_ip])

    @property
    def main_payload_data(self):
        res = {}
        for key in ['nameOnCard', 'cardNumber', 'client_ip', 'country',
                    'uniqueCC', 'payment_method', 'bin', 'eci']:
            value = self.payload_json.get(key)
            if value:
                res.update({key: value})

        return res

    def get_payload_dict(self):
        if settings.DATABASES.get(
                'default', {}).get('ENGINE') == 'django.db.backends.sqlite3':
            json_str = self.payload.replace("'", "\"")
            res = json.loads(json_str) if json_str else {}
        else:
            res = self.payload_json
        return res if res else {}


class Bank(TimeStampedModel, NamedModel):
    country = models.ForeignKey(Country, null=True, blank=True,
                                on_delete=models.DO_NOTHING)
    website = models.URLField(null=True, blank=True)
    phone = models.CharField(max_length=127, null=True, blank=True)

    def __str__(self):
        res = '{}'.format(self.name)
        if self.country:
            res += ' ({})'.format(self.country.country.code)
        return res


class CardCompany(TimeStampedModel, NamedModel):
    pass


class CardType(TimeStampedModel, NamedModel):
    pass


class CardLevel(TimeStampedModel, NamedModel):
    pass


class BankBin(TimeStampedModel):
    bank = models.ForeignKey(Bank, on_delete=models.DO_NOTHING, null=True,
                             blank=True)
    bin = models.CharField(null=False, default=None, unique=True,
                           max_length=15)
    card_company = models.ForeignKey(CardCompany, null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    card_type = models.ForeignKey(CardType, null=True, blank=True,
                                  on_delete=models.DO_NOTHING)
    card_level = models.ForeignKey(CardLevel, null=True, blank=True,
                                   on_delete=models.DO_NOTHING)
    checked_external = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if kwargs.pop('check_external_info', False) and self.bin:
            url = settings.BINCODES_BANK_URL
            res = requests.get(url.format(
                api_key=settings.BINCODES_API_KEY,
                bin=self.bin

            ))
            data = res.json()
            if res.status_code == 200 and data.get('valid') == 'true':
                bank = data.get('bank')
                card = data.get('card')
                card_type = data.get('type')
                level = data.get('level')
                country_code = data.get('countrycode')
                website = data.get('website')
                phone = data.get('phone')
                self.bank, _ = \
                    Bank.objects.get_or_create(name=bank) if bank else (None,
                                                                        False)
                if self.bank:
                    self.bank.country = Country.objects.get(
                        country=country_code
                    ) if country_code else None
                    self.bank.website = website if website else None
                    self.bank.phone = phone
                    self.bank.save()
                self.card_company, _ = \
                    CardCompany.objects.get_or_create(name=card) if card else (
                        None, False
                    )
                self.card_type, _ = \
                    CardType.objects.get_or_create(
                        name=card_type
                    ) if card_type else (None, False)
                self.card_level, _ = \
                    CardLevel.objects.get_or_create(name=level) if level else (
                        None, False
                    )
            self.checked_external = True

        super(BankBin, self).save(*args, **kwargs)

    def __str__(self):
        res = '{}'.format(self.bin)
        if self.bank:
            res += ' {}'.format(self.bank.__str__())
        return res
