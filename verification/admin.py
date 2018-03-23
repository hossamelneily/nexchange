from django.contrib import admin

from verification.models import Verification


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):

    list_display = ('id_status', 'util_status', 'full_name', 'note',
                    'name_on_card', 'unique_cc')
    readonly_fields = ('identity_document', 'utility_document', 'name_on_card',
                       'unique_cc', 'payment_preference', 'id_doc',
                       'residence_doc', 'user')

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
