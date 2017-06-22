from django.contrib import admin

from orders.models import Order


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ("price",)
    readonly_fields = (
        'is_paid_buy', 'ticker_amount', 'success_payments_amount',
        'success_payments_by_reference', 'success_payments_by_wallet',
        'bad_currency_payments')


admin.site.register(Order, OrderAdmin)
