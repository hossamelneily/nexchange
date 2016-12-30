from django.contrib import admin

from .models import Program, Referral, ReferralCode

admin.site.register(ReferralCode)
admin.site.register(Referral)
admin.site.register(Program)
admin.autodiscover()
