from django.contrib import admin

from .models import SuspiciousTransactions


@admin.register(SuspiciousTransactions)
class SuspiciousTransactionsAdmin(admin.ModelAdmin):
    list_display = ('tx_id', 'time', 'amount', 'address_from', 'address_to',
                    'currency', 'human_comment', 'approved')
    readonly_fields = ('auto_comment',)
    autocomplete_fields = ('currency',)
