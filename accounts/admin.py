from django.contrib import admin
from accounts.forms import BaseProfileForm

from accounts.models import Profile, SmsToken


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_on', 'time_zone', 'last_visit_time')
    form = BaseProfileForm
    search_fields = ('user__username', 'time_zone')


# Register your models here.
admin.site.register(SmsToken)
admin.site.register(Profile, ProfileAdmin)
