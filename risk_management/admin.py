from django.contrib import admin

from risk_management.models import Reserve, Account, Cover, ReserveLog,\
    PortfolioLog, PNL, PNLSheet


@admin.register(Reserve)
class ReserveAdmin(admin.ModelAdmin):
    readonly_fields = ('currency', 'balance', 'available', 'pending')
    list_display = ('currency', 'expected_balance', 'margin_balance',
                    'needed_trade_move', 'is_limit_reserve', 'balance')
    search_fields = ('currency__code', 'currency__name')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    readonly_fields = ('reserve', 'wallet', 'balance', 'available', 'pending')
    list_display = ('reserve', 'wallet', 'balance', 'available', 'pending',
                    'is_main_account')
    search_fields = ('wallet', 'reserve__currency__name',
                     'reserve__currency__code')


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
                    'volume_bid', 'average_ask', 'average_bid', 'exit_price')
    readonly_fields = ('position_str', 'base_position_str', 'realized_volume',
                       'pnl_realized', 'pnl_unrealized', 'pnl_str', 'pnl_btc',
                       'pnl_usd', 'pnl_eth', 'pnl_eur')
    search_fields = ('pair__name',)


@admin.register(PNLSheet)
class PNLSheetAdmin(admin.ModelAdmin):
    list_display = ('date_from', 'date_to')
    readonly_fields = ('pnl_btc', 'pnl_eth', 'pnl_eur',
                       'pnl_usd', 'positions', 'positions_str')
