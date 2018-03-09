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


admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.site.register(FailedRequest)
admin.autodiscover()
