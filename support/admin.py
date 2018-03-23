from django.contrib import admin

from .models import Support


class SupportAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_on', 'is_resolved']
    list_filter = ('is_resolved',)
    search_fields = ['user__username', ]
    readonly_fields = ['user', 'order']


admin.site.register(Support, SupportAdmin)
admin.autodiscover()
