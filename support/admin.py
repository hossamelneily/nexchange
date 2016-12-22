from django.contrib import admin
from .models import Support


class SupportAdmin(admin.ModelAdmin):
    list_display = ['name', 'created', 'is_resolved']


admin.site.register(Support, SupportAdmin)
admin.autodiscover()
