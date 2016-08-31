from django.contrib import admin
from .models import ReferralCode, Referral, Program, Balance

admin.register(ReferralCode)
admin.register(Referral)
admin.register(Program)
admin.register(Balance)
