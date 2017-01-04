from django.contrib import admin

from payments.models import PaymentMethod, PaymentPreference, UserCards

admin.site.register(PaymentMethod)
admin.site.register(PaymentPreference)
admin.site.register(UserCards)
admin.autodiscover()
