from django.contrib import admin

from orders.models import Order


class OrderAdmin(admin.ModelAdmin):

    readonly_fields = (
        'user', 'amount_quote', 'amount_base', 'unique_reference', 'status',
        'pair', 'withdraw_address', 'deposit_address', 'price',
        'user_provided_amount', 'ticker_amount_quote', 'order_type',
        'payment_preference', 'user_marked_as_paid', 'system_marked_as_paid',
        'is_default_rule', 'from_default_rule', 'exchange')

    search_fields = ('unique_reference', 'pair__base__code',
                     'pair__quote__code', 'pair__name', 'user__username')

    list_display = ('unique_reference', 'user', 'pair', 'amount_base',
                    'amount_quote', 'withdraw_address', 'deposit_address',
                    'status_name', 'created_on', 'flagged', 'expired')


admin.site.register(Order, OrderAdmin)
