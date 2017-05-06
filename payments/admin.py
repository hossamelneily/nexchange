from django.contrib import admin

from payments.models import (PaymentMethod, PaymentPreference,
                             Payment, FailedRequest)

admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.site.register(Payment)
admin.site.register(FailedRequest)
admin.autodiscover()
