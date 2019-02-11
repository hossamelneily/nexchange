from django.contrib import admin

from .models import SuspiciousTransactions, SuspiciousTransactionCategory
from core.models import Currency


class CurrencyFilter(admin.SimpleListFilter):
    title = 'Currency'
    parameter_name = 'currency'

    def lookups(self, request, model_admin):
        currencies = Currency.objects.filter(is_crypto=True)
        return [(currency, currency) for currency in currencies
                if currency.has_suspicious_transactions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(currency__code=self.value())
        else:
            return queryset


@admin.register(SuspiciousTransactions)
class SuspiciousTransactionsAdmin(admin.ModelAdmin):
    list_filter = ('categories', CurrencyFilter)
    list_display = ('tx_id', 'time', 'amount', 'address_from', 'address_to',
                    'currency', 'human_comment', 'approved')
    autocomplete_fields = ('currency', 'categories')


@admin.register(SuspiciousTransactionCategory)
class SuspiciousTransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
