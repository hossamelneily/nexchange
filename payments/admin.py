from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference

admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.autodiscover()
