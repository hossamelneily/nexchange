from django.contrib import admin

from risk_management.models import Reserve, Account, Cover, ReserveLog,\
    PortfolioLog, PNL, PNLSheet, DisabledCurrency, ReservesCover, \
    ReservesCoverSettings, PeriodicReservesCoverSettings


@admin.register(Reserve)
class ReserveAdmin(admin.ModelAdmin):
    readonly_fields = ('currency', 'balance', 'available', 'pending')
    list_display = ('currency', 'target_level', 'allowed_diff',
                    'needed_trade_move', 'is_limit_reserve', 'balance')
    search_fields = ('currency__code', 'currency__name')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    readonly_fields = ('reserve', 'wallet', 'balance', 'available', 'pending')
    list_display = ('reserve', 'description', 'balance', 'available',
                    'pending', 'is_main_account', 'disabled', 'healthy')
    search_fields = ('wallet', 'reserve__currency__name',
                     'reserve__currency__code', 'description')


@admin.register(Cover)
class CoverAdmin(admin.ModelAdmin):
    raw_id_fields = ('orders',)
    list_display = ('cover_type', 'pair', 'amount_base', 'amount_quote',
                    'account', 'cover_id')


@admin.register(ReserveLog)
class ReserveLogAdmin(admin.ModelAdmin):
    list_display = ('reserve', 'available', 'available_btc', 'available_usd',
                    'available_eur', 'available_eth', 'created_on',
                    'portfolio_log')
    search_fields = ('reserve__currency__name', 'reserve__currency__code')


@admin.register(PortfolioLog)
class PortfolioLogAdmin(admin.ModelAdmin):
    list_display = ('created_on', 'total_btc', 'total_usd', 'total_eur',
                    'total_eth', 'assets_str')
    readonly_fields = ('created_on', 'total_btc', 'total_usd', 'total_eur',
                       'total_eth', 'assets_str', 'assets_by_proportion')


@admin.register(PNL)
class PNLAdmin(admin.ModelAdmin):
    list_display = ('pnl_sheet', 'date_from', 'date_to', 'pair', 'volume_ask',
                    'volume_bid', 'average_ask', 'average_bid', 'exit_price',
                    'realized_volume', 'pnl_realized', 'pnl_unrealized',
                    'pnl_str')
    readonly_fields = ('position_str', 'base_position_str', 'realized_volume',
                       'pnl_realized', 'pnl_unrealized', 'pnl_str', 'pnl_btc',
                       'pnl_usd', 'pnl_eth', 'pnl_eur',
                       'average_base_position_price')
    search_fields = ('pair__name',)


@admin.register(PNLSheet)
class PNLSheetAdmin(admin.ModelAdmin):
    list_display = ('days', 'date_from', 'date_to', 'positions_str')
    readonly_fields = ('pnl_btc', 'pnl_eth', 'pnl_eur',
                       'pnl_usd', 'positions', 'positions_str')


@admin.register(DisabledCurrency)
class DisabledCurrencyAdmin(admin.ModelAdmin):
    list_display = ('currency', 'disable_quote', 'disable_base',
                    'user_visible_reason', 'admin_comment', 'created_on',
                    'modified_on', )


class CoverInline(admin.TabularInline):
    model = Cover
    readonly_fields = (
        'cover_type', 'pair', 'currency', 'amount_base', 'amount_quote',
        'rate', 'cover_id', 'account', 'status', 'orders',
    )
    can_delete = False


@admin.register(ReservesCover)
class ReservesCoverAdmin(admin.ModelAdmin):
    inlines = (CoverInline,)
    list_display = ('created_on', 'settings', 'pair', 'amount_base',
                    'amount_quote', 'static_rate_change_str', 'discard')
    readonly_fields = (
        'pair', 'amount_quote', 'amount_base', 'rate', 'acquisition_rate',
        'static_rate_change_str', 'pnl_rates',
        'sell_reserves_filtered', 'buy_reserves_filtered', 'sell_reserves',
        'buy_reserves', 'portfolio_log', 'pnl_sheets'
    )


@admin.register(ReservesCoverSettings)
class ReservesCoverSettingsAdmin(admin.ModelAdmin):
    list_display = ('currencies_str', 'coverable_str', 'default',)


@admin.register(PeriodicReservesCoverSettings)
class PeriodicReservesCoverSettingsAdmin(admin.ModelAdmin):
    list_display = ('settings', 'str_minimum_rate_change',)
