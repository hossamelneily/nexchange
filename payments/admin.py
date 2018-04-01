from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference, Payment, \
    FailedRequest, PushRequest


@admin.register(PushRequest)
class PushRequestAdmin(admin.ModelAdmin):
    list_display = ('created_on', 'payment', 'valid_checksum', 'valid_ip',
                    'valid_timestamp', 'payment_created')
    readonly_fields = ('payment', 'valid_checksum', 'valid_timestamp',
                       'valid_ip', 'payment_created', 'url',
                       'payload', 'ip', 'payload_json', 'response')
    raw_id_fields = ('payment',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('amount_cash', 'currency', 'type')
    raw_id_fields = ('order',)


@admin.register(PaymentPreference)
class PaymentPreferenceAdmin(admin.ModelAdmin):
    readonly_fields = (
        'payment_method', 'secondary_identifier', 'provider_system_id',
        'is_verified', 'out_of_limit', 'total_payments_usd', 'currency',
        'buy_enabled', 'sell_enabled', 'location', 'cvv', 'ccexp',
        'physical_address_owner', 'bic', 'physical_address_bank', 'name',
        'beneficiary'
    )
    list_display = ('payment_method', 'secondary_identifier',
                    'provider_system_id', 'is_verified',
                    'out_of_limit', 'is_immediate_payment', 'tier',
                    'total_payments_usd')
    raw_id_fields = ('user',)


admin.site.register(PaymentMethod)
admin.site.register(FailedRequest)
admin.autodiscover()
