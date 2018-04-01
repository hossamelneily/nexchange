from django.contrib import admin

from verification.models import Verification, VerificationTier, TradeLimit


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):

    list_display = ('id_status', 'util_status', 'full_name', 'note',
                    'name_on_card', 'unique_cc')
    readonly_fields = ('identity_document', 'utility_document', 'name_on_card',
                       'unique_cc', 'payment_preference', 'id_doc',
                       'residence_doc', 'user', 'user_input_comment',
                       'total_payments_usd', 'out_of_limits',
                       'is_immediate_payment', 'tier')

    search_fields = ('note', 'full_name', 'id_status', 'util_status',
                     'payment_preference__secondary_identifier')

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
