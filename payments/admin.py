from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference, Payment, \
    FailedRequest, PushRequest, Country, Bank, BankBin
from verification.models import Verification
from verification.admin import VerificationDocumentInline
import nested_admin


class VerificationInline(nested_admin.NestedTabularInline):
    model = Verification
    extra = 0
    fk_name = 'payment_preference'
    inlines = [VerificationDocumentInline]
    exclude = (
        'user', 'utility_document', 'identity_document', 'disabled',
        'id_status', 'util_status'
    )
    readonly_fields = ('note',)


@admin.register(PushRequest)
class PushRequestAdmin(admin.ModelAdmin):
    list_display = ('created_on', 'payment', 'valid_checksum', 'valid_ip',
                    'valid_timestamp', 'payment_created')
    readonly_fields = ('payment', 'valid_checksum', 'valid_timestamp',
                       'valid_ip', 'payment_created', 'url',
                       'payload', 'ip', 'payload_json', 'response',
                       'main_payload_data')
    search_fields = ('payment__order__unique_reference',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('amount_cash', 'currency', 'type',
                    'payment_system_id', 'secondary_payment_system_id')
    readonly_fields = (
        'amount_cash', 'currency', 'type', 'payment_system_id',
        'secondary_payment_system_id', 'is_redeemed', 'is_success',
        'is_complete', 'payment_preference', 'order', 'reference', 'user',
        'limit_order'
    )
    autocomplete_fields = ('order',)
    search_fields = ('order__unique_reference', 'currency__code',
                     'payment_system_id', 'secondary_payment_system_id')


@admin.register(PaymentPreference)
class PaymentPreferenceAdmin(nested_admin.NestedModelAdmin):
    inlines = [VerificationInline]
    readonly_fields = (
        'payment_method', 'secondary_identifier', 'provider_system_id',
        'is_verified', 'out_of_limit', 'total_payments_usd', 'currency',
        'buy_enabled', 'sell_enabled', 'location', 'cvv', 'ccexp',
        'physical_address_owner', 'bic', 'physical_address_bank', 'name',
        'beneficiary', 'push_request', 'bank_bin'
    )
    list_display = ('payment_method', 'secondary_identifier',
                    'provider_system_id', 'is_verified',
                    'out_of_limit', 'is_immediate_payment', 'tier',
                    'total_payments_usd')
    autocomplete_fields = ('user', 'push_request', 'tier')
    search_fields = ('secondary_identifier', 'provider_system_id')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    autocomplete_fields = ('allowed_countries', 'minimal_fee_currency')


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ('country',)


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'website', 'phone')
    autocomplete_fields = ('country',)
    search_fields = ('name',)


@admin.register(BankBin)
class BankBinAdmin(admin.ModelAdmin):
    list_display = ('bin', 'bank', 'card_company', 'card_type', 'card_level',
                    'checked_external')
    autocomplete_fields = ('bank',)
    search_fields = ('bin', 'bank__name', 'card_company__name')


admin.site.register(FailedRequest)
