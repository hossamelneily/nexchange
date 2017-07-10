from django.contrib import admin

from accounts.models import Profile, SmsToken


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_on', 'time_zone', 'last_visit_time')


# Register your models here.
admin.site.register(SmsToken)
admin.site.register(Profile, ProfileAdmin)
