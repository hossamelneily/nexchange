from django.contrib import admin
from core.models import Currency, Profile, Order, SmsToken, PaymentMethod,\
    Address, PaymentPreference, Payment, CmsPage, \
    BraintreePayment, BraintreePaymentMethod

admin.site.register(Currency)
admin.site.register(Profile)
admin.site.register(Order)
admin.site.register(SmsToken)
admin.site.register(PaymentMethod)
admin.site.register(Payment)
admin.site.register(PaymentPreference)
admin.site.register(Address)
admin.site.register(CmsPage)
admin.site.register(BraintreePayment)
admin.site.register(BraintreePaymentMethod)
admin.autodiscover()
