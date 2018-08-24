from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference, Payment, \
    FailedRequest, PushRequest, Country


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
        'is_complete', 'payment_preference', 'order', 'reference', 'user'
    )
    autocomplete_fields = ('order',)
    search_fields = ('order__unique_reference', 'currency__code',
                     'payment_system_id', 'secondary_payment_system_id')


@admin.register(PaymentPreference)
class PaymentPreferenceAdmin(admin.ModelAdmin):
    readonly_fields = (
        'payment_method', 'secondary_identifier', 'provider_system_id',
        'is_verified', 'out_of_limit', 'total_payments_usd', 'currency',
        'buy_enabled', 'sell_enabled', 'location', 'cvv', 'ccexp',
        'physical_address_owner', 'bic', 'physical_address_bank', 'name',
        'beneficiary', 'push_request'
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


admin.site.register(FailedRequest)
