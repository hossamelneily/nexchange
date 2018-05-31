from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference, Payment, \
    FailedRequest, PushRequest


@admin.register(PushRequest)
class PushRequestAdmin(admin.ModelAdmin):
    list_display = ('created_on', 'payment', 'valid_checksum', 'valid_ip',
                    'valid_timestamp', 'payment_created')
    readonly_fields = ('payment', 'valid_checksum', 'valid_timestamp',
                       'valid_ip', 'payment_created', 'url',
                       'payload', 'ip', 'payload_json', 'response',
                       'main_payload_data')
    raw_id_fields = ('payment',)
    search_fields = ('payment__order__unique_reference',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('amount_cash', 'currency', 'type', 'payment_system_id',
                    'secondary_payment_system_id')
    readonly_fields = (
        'amount_cash', 'currency', 'type', 'payment_system_id',
        'secondary_payment_system_id', 'is_redeemed', 'is_success',
        'is_complete', 'payment_preference', 'order', 'reference', 'user'
    )
    raw_id_fields = ('order',)
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
    raw_id_fields = ('user', 'push_request')
    search_fields = ('secondary_identifier', 'provider_system_id')


admin.site.register(PaymentMethod)
admin.site.register(FailedRequest)
admin.autodiscover()
