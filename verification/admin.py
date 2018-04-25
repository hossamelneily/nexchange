from django.contrib import admin

from verification.models import Verification, VerificationTier, TradeLimit
from orders.models import Order
from payments.models import Payment


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):

    list_display = ('created_on', 'id_status', 'util_status', 'full_name',
                    'note', 'name_on_card', 'unique_cc')
    readonly_fields = ('identity_document', 'utility_document', 'name_on_card',
                       'unique_cc', 'payment_preference', 'id_doc',
                       'residence_doc', 'user', 'user_input_comment',
                       'total_payments_usd', 'out_of_limits',
                       'is_immediate_payment', 'tier')

    search_fields = ('note', 'full_name', 'id_status', 'util_status',
                     'payment_preference__secondary_identifier',
                     'payment_preference__provider_system_id',
                     'user__username',
                     'payment_preference__user__username')

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(VerificationAdmin, self).\
            get_search_results(request, queryset, search_term)
        try:
            orders = Order.objects.filter(exchange=False,
                                          unique_reference=search_term)
            if orders:
                payments = Payment.objects.filter(order__in=orders)
                prefs = [p.payment_preference for p in payments]
                queryset |= self.model.objects.filter(
                    payment_preference__in=prefs)
        except Exception:
            pass
        return queryset, use_distinct

    def name_on_card(self, obj):
        name = ''
        if obj.payment_preference:
            name = obj.payment_preference.secondary_identifier
        return name

    def unique_cc(self, obj):
        unique_cc = ''
        if obj.payment_preference:
            unique_cc = obj.payment_preference.provider_system_id
        return unique_cc

    def total_payments_usd(self, obj):
        unique_cc = ''
        if obj.payment_preference:
            unique_cc = obj.payment_preference.total_payments_usd
        return unique_cc

    def out_of_limits(self, obj):
        unique_cc = ''
        if obj.payment_preference:
            unique_cc = obj.payment_preference.out_of_limits
        return unique_cc

    def is_immediate_payment(self, obj):
        unique_cc = ''
        if obj.payment_preference:
            unique_cc = obj.payment_preference.is_immediate_payment
        return unique_cc

    def tier(self, obj):
        unique_cc = ''
        if obj.payment_preference:
            unique_cc = obj.payment_preference.tier
        return unique_cc


@admin.register(VerificationTier)
class VerificationTierAdmin(admin.ModelAdmin):
    pass


@admin.register(TradeLimit)
class TradeLimitAdmin(admin.ModelAdmin):
    pass
