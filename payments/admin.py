from django.contrib import admin

from payments.models import (PaymentMethod, PaymentPreference,
                             Payment, FailedRequest)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('amount_cash', 'currency', 'type')
    raw_id_fields = ('order',)


admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.site.register(FailedRequest)
admin.autodiscover()
