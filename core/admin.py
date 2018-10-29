from django.contrib import admin
from core.models import Currency, Transaction, Address, \
    Pair, Location, AddressReserve, TransactionApiMapper, Market, \
    TransactionPrice, CurrencyAlgorithm
from core.common.models import Flag


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'user', 'currency', 'disabled')
    raw_id_fields = ('reserve', 'user',)
    search_fields = (
        'currency__code', 'address'
    )
    autocomplete_fields = ('currency', 'user')


@admin.register(AddressReserve)
class AddressReserveAdmin(admin.ModelAdmin):
    list_display = ('card_id', 'user', 'currency', 'disabled')
    search_fields = (
        'currency__code',
    )
    autocomplete_fields = ('currency', 'user')


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_crypto')
    search_fields = (
        'code', 'name'
    )


@admin.register(Pair)
class PairAdmin(admin.ModelAdmin):
    list_display = ('name', 'fee_ask', 'fee_bid', 'disabled', 'test_mode',
                    'last_price_saved')
    search_fields = (
        'base__code', 'quote__code', 'name'
    )
    autocomplete_fields = ('base', 'quote')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('amount', 'currency', 'type', 'order')
    raw_id_fields = ('order', 'address_from', 'address_to')
    readonly_fields = ('reserves_cover', 'limit_order')
    search_fields = (
        'address_to__address', 'address_from__address', 'tx_id', 'tx_id_api',
        'order__unique_reference', 'type', 'currency__code', 'currency__name',
    )
    autocomplete_fields = ('order', 'address_to', 'address_from', 'currency',
                           'refunded_transaction')


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_main_market')
    readonly_fields = ('name', 'code', 'is_main_market')


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ('flag_val', 'model_name', 'flagged_id')
    search_fields = ('flag_val', 'model_name', 'flagged_id')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'firstname', 'lastname', 'country', 'zip')
    autocomplete_fields = ('user',)


@admin.register(TransactionPrice)
class TransactionPriceAdmin(admin.ModelAdmin):
    list_display = ('amount', 'limit', 'algo', 'description')


@admin.register(CurrencyAlgorithm)
class CurrencyAlgorithmAdmin(admin.ModelAdmin):
    list_display = ('name',)


admin.site.register(TransactionApiMapper)
