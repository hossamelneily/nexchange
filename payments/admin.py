from django.contrib import admin
from payments.models import PaymentPreference, PaymentMethod

admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.autodiscover()
