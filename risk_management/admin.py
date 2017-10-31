from django.contrib import admin

from risk_management.models import Reserve, Account


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
