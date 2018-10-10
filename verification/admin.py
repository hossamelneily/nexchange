from django.contrib import admin

from verification.models import Verification, VerificationTier, TradeLimit,\
    VerificationDocument, DocumentType, VerificationCategory, CategoryRule,\
    KycPushRequest
from orders.models import Order
from payments.models import Payment
from django.contrib.admin import SimpleListFilter
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .signals.add_kyc_groups import raw_add_kyc_groups


class VerificationInline(admin.TabularInline):
    model = VerificationDocument
    exclude = ('document_file',)
    readonly_fields = ('kyc_push', 'image_tag', 'whitelisted_address')
    autocomplete_fields = ('document_type',)
    fk_name = 'verification'


class PendingFilter(SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('PENDING', 'PENDING'),
            ('BAD NAME', 'BAD NAME'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'PENDING':
            return queryset.filter(pk__in=[
                v.pk for v in queryset if v.has_pending_documents
            ])
        if self.value() == 'BAD NAME':
            return queryset.filter(pk__in=[
                v.pk for v in queryset if v.has_approved_documents and
                v.has_bad_name
            ])
        return queryset


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    inlines = [
        VerificationInline,
    ]

    list_filter = (PendingFilter, 'category')
    list_display = ('created_on', 'id_document_status', 'util_document_status',
                    'full_name', 'note', 'admin_comment', 'user',
                    'name_on_card', 'unique_cc', 'name_on_card_matches',
                    'out_of_limit', 'flagged_str')
    exclude = ('identity_document', 'utility_document')
    readonly_fields = (
        'note', 'name_on_card',
        'name_on_card_matches', 'bad_name_verifications', 'unique_cc',
        'bank_bin', 'main_card_data', 'payment_preference', 'id_doc',
        'residence_doc', 'user', 'user_input_comment', 'total_payments_usd',
        'total_payments_usd_1day', 'total_payments_usd_30days', 'out_of_limit',
        'is_immediate_payment', 'tier', 'util_status', 'id_status',
        'modified_by', 'created_by', 'related_orders', 'referred_with'
    )

    search_fields = ('note', 'full_name', 'id_status', 'util_status',
                     'payment_preference__secondary_identifier',
                     'payment_preference__provider_system_id',
                     'user__username',
                     'payment_preference__user__username')
    autocomplete_fields = ('category',)

    def save_model(self, request, obj, form, change):
        super(VerificationAdmin, self).save_model(request, obj, form, change)
        if obj.has_bad_name:
            _name_on_card = self.name_on_card(obj)
            messages.add_message(
                request,
                messages.ERROR,
                'Verification {} has bad name. "{}" != "{}"'.format(
                    obj.pk, obj.full_name, _name_on_card
                )
            )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(VerificationAdmin, self).\
            get_search_results(request, queryset, search_term)
        try:
            orders = Order.objects.filter(exchange=False,
                                          unique_reference=search_term)
            if orders:
                payments = Payment.objects.filter(order__in=orders)
                prefs = [p.payment_preference for p in payments]
                queryset |= self.model.objects.filter(
                    payment_preference__in=prefs)
        except Exception:
            pass
        return queryset, use_distinct

    def _get_payment_preference_field(self, obj, param_name):
        res = ''
        if obj.payment_preference:
            res = getattr(obj.payment_preference, param_name)
        return res

    def bank_bin(self, obj):
        return self._get_payment_preference_field(obj, 'bank_bin')

    def main_card_data(self, obj):
        push_request = self._get_payment_preference_field(obj, 'push_request')
        if push_request:
            return push_request.main_payload_data
        return {}

    def name_on_card(self, obj):
        return self._get_payment_preference_field(obj, 'secondary_identifier')

    @mark_safe
    def name_on_card_matches(self, obj):
        res = self._get_payment_preference_field(obj, 'name_on_card_matches')
        _color = 'green' if res else 'red'
        return '<b style="background:{};">{}</b>'.format(_color, res)

    def bad_name_verifications(self, obj):
        records = self._get_payment_preference_field(obj,
                                                     'bad_name_verifications')
        return [record.pk for record in records]

    def unique_cc(self, obj):
        return self._get_payment_preference_field(obj, 'provider_system_id')

    def total_payments_usd(self, obj):
        return self._get_payment_preference_field(obj, 'total_payments_usd')

    def total_payments_usd_1day(self, obj):
        fn = self._get_payment_preference_field(
            obj, 'get_successful_payments_amount'
        )
        if callable(fn):
            return fn(days=1)

    def total_payments_usd_30days(self, obj):
        fn = self._get_payment_preference_field(
            obj, 'get_successful_payments_amount'
        )
        if callable(fn):
            return fn(days=30)

    @mark_safe
    def out_of_limit(self, obj):
        res = self._get_payment_preference_field(obj, 'out_of_limit')
        _color = 'red' if res else 'green'
        return '<b style="background:{};">{}</b>'.format(_color, res)

    @mark_safe
    def flagged_str(self, obj):
        res = obj.flagged
        _color = 'red' if res else 'green'
        return '<b style="background:{};">{}</b>'.format(_color, res)

    @mark_safe
    def is_immediate_payment(self, obj):
        res = self._get_payment_preference_field(obj, 'is_immediate_payment')
        _color = 'green' if res else 'red'
        return '<b style="background:{};">{}</b>'.format(_color, res)

    def tier(self, obj):
        return self._get_payment_preference_field(obj, 'tier')

    def save_related(self, request, form, formsets, change):
        super(VerificationAdmin, self).save_related(request, form, formsets,
                                                    change)
        # this is important cause adding many2many fields (category) with
        # django-admin isint working properly due to "cleaning"
        raw_add_kyc_groups(form.instance)


@admin.register(VerificationTier)
class VerificationTierAdmin(admin.ModelAdmin):
    search_fields = ('name', 'description')
    autocomplete_fields = ('required_documents',)


@admin.register(TradeLimit)
class TradeLimitAdmin(admin.ModelAdmin):
    autocomplete_fields = ('currency', 'tier',)
    pass


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'document_status', 'document_type', 'full_name', 'note',
        'admin_comment', 'user', 'name_on_card', 'unique_cc'
    )
    exclude = ('document_file',)
    readonly_fields = (
        'image_tag', 'whitelisted_address',
        'note', 'verification', 'name_on_card', 'unique_cc',
        'payment_preference', 'user', 'user_input_comment',
        'total_payments_usd', 'out_of_limit', 'is_immediate_payment', 'tier',
        'modified_by', 'created_by'
    )
    autocomplete_fields = ('document_type',)

    def save_model(self, request, obj, form, change):
        super(VerificationDocumentAdmin, self).save_model(request, obj, form,
                                                          change)
        _ver = obj.verification

        if _ver and _ver.has_bad_name:
            _name_on_card = self.name_on_card(obj)
            _path = reverse(
                'admin:verification_verification_change', args=[_ver.pk]
            )
            _link = format_html('<a href="{}">{}</a>', _path, _ver.note)
            messages.add_message(
                request,
                messages.ERROR,
                format_html(
                    'Verification object {} has bad name. "{}" != "{}"',
                    _link, _ver.full_name, _name_on_card
                )
            )

    def _get_verification_field(self, obj, param_name):
        res = ''
        if obj.verification:
            res = getattr(obj.verification, param_name)
        return res

    def payment_preference(self, obj):
        return self._get_verification_field(obj, 'payment_preference')

    def user(self, obj):
        return self._get_verification_field(obj, 'user')

    def note(self, obj):
        return self._get_verification_field(obj, 'note')

    def full_name(self, obj):
        return self._get_verification_field(obj, 'full_name')

    def user_input_comment(self, obj):
        return self._get_verification_field(obj, 'user_input_comment')

    def _get_payment_preference_field(self, obj, param_name):
        res = ''
        if obj.verification and obj.verification.payment_preference:
            res = getattr(obj.verification.payment_preference, param_name)
        return res

    def name_on_card(self, obj):
        return self._get_payment_preference_field(obj, 'secondary_identifier')

    def unique_cc(self, obj):
        return self._get_payment_preference_field(obj, 'provider_system_id')

    def total_payments_usd(self, obj):
        return self._get_payment_preference_field(obj, 'total_payments_usd')

    def out_of_limit(self, obj):
        return self._get_payment_preference_field(obj, 'out_of_limit')

    def is_immediate_payment(self, obj):
        return self._get_payment_preference_field(obj, 'is_immediate_payment')

    def tier(self, obj):
        return self._get_payment_preference_field(obj, 'tier')


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    search_fields = ('name', 'description', 'api_key')


@admin.register(VerificationCategory)
class VerificationCateroryAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name', 'flagable')
    autocomplete_fields = ('banks', 'rules')


@admin.register(CategoryRule)
class CategoryRuleAdmin(admin.ModelAdmin):
    search_fields = ('name', 'key', 'value', 'rule_type')
    list_display = ('name', 'key', 'value', 'rule_type')


@admin.register(KycPushRequest)
class KycPushRequestAdmin(admin.ModelAdmin):
    list_display = (
        'created_on', 'full_name', 'birth_date', 'doc_expiration',
        'identification_status', 'identification_approved', 'valid_link'
    )
    readonly_fields = (
        'url', 'payload', 'ip', 'payload_json', 'identification_status',
        'identification_approved', 'valid_link', 'full_name', 'nationality',
        'issuing_country', 'selected_country', 'birth_date', 'doc_expiration',
        'response'
    )
    search_fields = ('full_name', 'birth_date')
