from django.contrib import admin
from .models import Subscription, Category, UtmSource
from django.contrib.admin import SimpleListFilter
from decimal import Decimal


@admin.register(UtmSource)
class UtmSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'comment')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


class BalanceFilter(SimpleListFilter):
    title = 'Adrress ETH Balance'
    parameter_name = 'eth_balance'

    def lookups(self, request, model_admin):
        return [
            ('0.1', '>0.1 ETH'),
            ('1', '>1 ETH'),
            ('10', '>10 ETH'),
            ('100', '>100 ETH'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(eth_balance__gt=Decimal(self.value()))
        return queryset


class AddressTurnoverFilter(BalanceFilter):
    title = 'Adrress ETH Turnover'
    parameter_name = 'address_turnover'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(address_turnover__gt=Decimal(self.value()))
        return queryset


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_filter = (
        'potential', 'category', 'utm_source', BalanceFilter,
        AddressTurnoverFilter
    )
    readonly_fields = ('sending_address', 'contribution', )
    list_display = ('email', 'sending_address', 'user_comment',
                    'admin_comment', 'eth_balance', 'address_turnover',
                    'potential', 'utm_source', 'category_names')
    search_fields = ('sending_address', 'email', 'admin_comment',
                     'user_comment')
    raw_id_fields = ('users', 'orders', )
