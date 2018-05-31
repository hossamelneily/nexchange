from django.contrib import admin
from core.models import Currency, Transaction, Address, \
    Pair, Location, AddressReserve, TransactionApiMapper, Market
from core.common.models import Flag


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'user', 'currency', 'disabled')
    search_fields = (
        'currency__code', 'address'
    )


@admin.register(AddressReserve)
class AddressReserveAdmin(admin.ModelAdmin):
    list_display = ('card_id', 'user', 'currency', 'disabled')
    search_fields = (
        'currency__code',
    )


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_crypto')
    search_fields = (
        'code', 'name'
    )


@admin.register(Pair)
class PairAdmin(admin.ModelAdmin):
    list_display = ('name', 'fee_ask', 'fee_bid', 'disabled', 'test_mode')
    search_fields = (
        'base__code', 'quote__code', 'name'
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('amount', 'currency', 'type', 'order')
    raw_id_fields = ('order', 'address_from', 'address_to')
    readonly_fields = ('reserves_cover',)
    search_fields = (
        'address_to__address', 'address_from__address', 'tx_id', 'tx_id_api',
        'order__unique_reference', 'type', 'currency__code', 'currency__name',
    )


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_main_market')
    readonly_fields = ('name', 'code', 'is_main_market')


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ('flag_val', 'model_name', 'flagged_id')
    search_fields = ('flag_val', 'model_name', 'flagged_id')


admin.site.register(Location)
admin.site.register(TransactionApiMapper)
