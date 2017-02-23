from django.contrib import admin
from core.models import Currency, Transaction, Address, Pair
from core.common.models import Flag


class TaskMetaAdmin(admin.ModelAdmin):
    readonly_fields = ('result',)


admin.site.register(Currency)
admin.site.register(Transaction)
admin.site.register(Address)
admin.site.register(Pair)
admin.site.register(Flag)
admin.autodiscover()
