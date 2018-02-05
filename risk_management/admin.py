from django.contrib import admin

from risk_management.models import Reserve, Account, Cover, ReserveLog,\
    PortfolioLog


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
