from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    readonly_fields = ('sending_address', 'contribution', )
    list_display = ('email', 'sending_address', 'user_comment',
                    'admin_comment', )
    search_fields = ('sending_address', 'email', )
    raw_id_fields = ('users', 'orders', )
