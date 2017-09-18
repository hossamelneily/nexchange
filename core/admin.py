from django.contrib import admin
from core.models import Currency, Transaction, Address, \
    Pair, Location, AddressReserve, TransactionApiMapper
from core.common.models import Flag


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'user', 'currency', 'disabled')


class AddressReserveAdmin(admin.ModelAdmin):
    list_display = ('card_id', 'user', 'currency', 'disabled',
                    'need_balance_check')


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_crypto')


class PairAdmin(admin.ModelAdmin):
    list_display = ('name', 'fee_ask', 'fee_bid', 'disabled')


class TranmsactionAdmin(admin.ModelAdmin):
    list_display = ('amount', 'currency', 'type', 'order')
    raw_id_fields = ('order', 'address_from', 'address_to')


admin.site.register(AddressReserve, AddressReserveAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Transaction, TranmsactionAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Pair, PairAdmin)
admin.site.register(Flag)
admin.site.register(Location)
admin.site.register(TransactionApiMapper)
admin.autodiscover()
