from django.contrib import admin

from orders.models import Order


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ('price', 'withdraw_address', 'deposit_address', 'user')
    readonly_fields = (
        'is_paid_buy', 'ticker_amount_quote', 'success_payments_amount',
        'success_payments_by_reference', 'success_payments_by_wallet',
        'bad_currency_payments', 'order_type')
    search_fields = ('unique_reference', 'pair__base__code',
                     'pair__quote__code', 'pair__name', 'user__username')


admin.site.register(Order, OrderAdmin)
