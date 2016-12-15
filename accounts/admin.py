from django.contrib import admin
from accounts.models import Profile, SmsToken

# Register your models here.
admin.site.register(SmsToken)
admin.site.register(Profile)
