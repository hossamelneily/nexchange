from django.contrib import admin

from .models import Support


class SupportAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created', 'is_resolved']
    list_filter = ('is_resolved',)
    search_fields = ['user__username', ]


admin.site.register(Support, SupportAdmin)
admin.autodiscover()
