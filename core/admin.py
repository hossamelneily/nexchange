from django.contrib import admin
from core.models import Currency, Profile, Order, SmsToken,\
    Address, CmsPage, Balance
from payments.models import PaymentMethod, PaymentPreference,\
    Payment, PaymentCredentials

admin.site.register(Currency)
admin.site.register(Profile)
admin.site.register(Order)
admin.site.register(SmsToken)
admin.site.register(PaymentMethod)
admin.site.register(Payment)
admin.site.register(PaymentPreference)
admin.site.register(Address)
admin.site.register(CmsPage)
admin.site.register(PaymentCredentials)
admin.site.register(Balance)
admin.autodiscover()
