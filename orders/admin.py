from django.contrib import admin

from orders.models import Order, LimitOrder, Trade, OrderBook


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    readonly_fields = (
        'referred_with', 'user', 'amount_quote', 'amount_base',
        'unique_reference', 'status', 'pair', 'withdraw_address',
        'deposit_address', 'refund_address', 'payment_id', 'price',
        'user_provided_amount', 'ticker_amount_quote', 'order_type',
        'payment_preference', 'user_marked_as_paid', 'system_marked_as_paid',
        'is_default_rule', 'from_default_rule', 'exchange', 'set_as_paid_on',
        'slippage', 'destination_tag', 'disabled', 'deleted'
    )

    search_fields = ('unique_reference', 'pair__base__code',
                     'pair__quote__code', 'pair__name', 'user__username',
                     'deposit_address__address', 'withdraw_address__address',
                     'refund_address__address', 'user__referral__code__code',
                     'user__referral__code__user__username'
                     )

    list_display = ('unique_reference', 'user', 'pair', 'amount_base',
                    'amount_quote', 'withdraw_address', 'deposit_address',
                    'payment_id', 'status', 'created_on', 'referred_with',
                    'flagged', 'expired')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LimitOrder)
class LimitOrderAdmin(admin.ModelAdmin):
    readonly_fields = ('unique_reference',)
    list_display = (
        'unique_reference', 'order_type', 'pair', 'amount_base',
        'amount_quote', 'limit_rate', 'rate', 'status', 'book_status'
    )
    readonly_fields = (
        'unique_reference', 'order_type', 'pair', 'amount_base',
        'amount_quote', 'limit_rate', 'rate', 'status', 'book_status',
        'withdraw_address', 'deposit_address', 'refund_address', 'user',
        'exchange', 'closed_amount_base', 'closed_amount_quote', 'order_book',
        'payment_id', 'destination_tag'
    )
    autocomplete_fields = ('pair',)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = (
        'unique_reference', 'pair', 'amount_base',
        'amount_quote', 'rate'
    )
    readonly_fields = (
        'unique_reference', 'pair', 'amount_base',
        'amount_quote', 'rate', 'sell_order', 'buy_order', 'order_book'
    )
    autocomplete_fields = ('pair',)


@admin.register(OrderBook)
class OrderBookAdmin(admin.ModelAdmin):
    readonly_fields = ('pair',)
    list_display = (
        'pair', 'created_on', 'disabled', 'flagged'
    )
    exclude = ('book_obj',)
