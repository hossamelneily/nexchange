from django.contrib import admin
from core.models import Currency, Transaction, Address, Pair


class TaskMetaAdmin(admin.ModelAdmin):
    readonly_fields = ('result',)


admin.site.register(Currency)
admin.site.register(Transaction)
admin.site.register(Address)
admin.site.register(Pair)
admin.autodiscover()
