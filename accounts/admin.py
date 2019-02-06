from django.contrib import admin
from accounts.forms import BaseProfileForm
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from accounts.models import Profile, SmsToken


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_on', 'time_zone', 'last_visit_time',
                    'agree_with_terms_and_conditions')
    readonly_fields = ('agree_with_terms_and_conditions','affiliate_address')
    autocomplete_fields = ('user','duplicate_of','tier')
    form = BaseProfileForm
    search_fields = ('user__username', 'time_zone')


class NexchangeUserAdmin(UserAdmin):
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            perm_fields = ('is_active', 'is_staff', 'is_superuser',
                           'groups', 'user_permissions')
        else:
            # modify these to suit the fields you want your
            # staff user to be able to edit
            perm_fields = ('is_active', 'is_staff', 'groups',
                           'user_permissions')

        return [(None, {'fields': ('username', 'password')}),
                (_('Personal info'),
                 {'fields': ('first_name', 'last_name', 'email')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'),
                 {'fields': ('last_login', 'date_joined')})]


# Register your models here.
admin.site.unregister(User)
admin.site.register(User, NexchangeUserAdmin)
admin.site.register(SmsToken)
admin.site.register(Profile, ProfileAdmin)
