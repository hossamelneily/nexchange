from django.contrib import admin

from verification.models import Verification, VerificationTier, TradeLimit,\
    VerificationDocument, DocumentType
from orders.models import Order
from payments.models import Payment


class VerificationInline(admin.TabularInline):
    model = VerificationDocument
    readonly_fields = ('document_type', 'document_file', 'download_document')


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    inlines = [
        VerificationInline,
    ]

    list_display = ('created_on', 'id_document_status', 'util_document_status',
                    'full_name', 'note', 'user',
                    'name_on_card', 'unique_cc')
    readonly_fields = ('identity_document', 'utility_document', 'note',
                       'name_on_card', 'unique_cc', 'payment_preference',
                       'id_doc', 'residence_doc', 'user', 'user_input_comment',
                       'total_payments_usd', 'out_of_limit',
                       'is_immediate_payment', 'tier', 'util_status',
                       'id_status')

    search_fields = ('note', 'full_name', 'id_status', 'util_status',
                     'payment_preference__secondary_identifier',
                     'payment_preference__provider_system_id',
                     'user__username',
                     'payment_preference__user__username')

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


@admin.register(VerificationTier)
class VerificationTierAdmin(admin.ModelAdmin):
    pass


@admin.register(TradeLimit)
class TradeLimitAdmin(admin.ModelAdmin):
    pass


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_status', 'document_type', 'full_name', 'note',
                    'user', 'name_on_card', 'unique_cc')
    readonly_fields = ('document_type', 'document_file', 'download_document',
                       'note', 'verification', 'name_on_card',
                       'unique_cc', 'payment_preference', 'user',
                       'user_input_comment',
                       'total_payments_usd', 'out_of_limit',
                       'is_immediate_payment', 'tier')

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
    pass
