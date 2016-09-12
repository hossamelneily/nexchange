from django.contrib import admin
from .models import ReferralCode, Referral, Program, Balance

admin.site.register(ReferralCode)
admin.site.register(Referral)
admin.site.register(Program)
admin.site.register(Balance)
admin.autodiscover()
