from django.contrib import admin
from .models import Subscription, Category, UtmSource
from django.contrib.admin import SimpleListFilter
from decimal import Decimal


@admin.register(UtmSource)
class UtmSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'comment')
    raw_id_fields = ('referral_codes',)


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


class TokensBalanceFilter(BalanceFilter):
    title = 'Tokens balance'
    parameter_name = 'tokens_balance_eth'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                tokens_balance_eth__gt=Decimal(self.value())
            )
        return queryset


class RelatedTurnoverFilter(BalanceFilter):
    title = 'Related Turnover'
    parameter_name = 'related_turnover'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(related_turnover__gt=Decimal(self.value()))
        return queryset


class AddressFilter(SimpleListFilter):
    title = 'Sending Address'
    parameter_name = 'sending_address'

    def lookups(self, request, model_admin):
        return [
            (True, 'Not defined'),
            (False, 'Defined'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            val = True if self.value() == 'True' else False
            if val:
                return queryset.filter(sending_address__in=[None, ''])
            else:
                return queryset.exclude(
                    sending_address='').exclude(sending_address='')
        return queryset


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_filter = (
        'potential', 'category', 'utm_source', BalanceFilter,
        TokensBalanceFilter, AddressTurnoverFilter, RelatedTurnoverFilter,
        AddressFilter,
    )
    readonly_fields = ('sending_address', 'contribution', 'users', 'orders',
                       'eth_balance', 'tokens_balance_eth',
                       'address_turnover', 'related_turnover',
                       'token_balances', 'non_zero_tokens', 'tokens_count')
    list_display = ('email', 'sending_address', 'user_comment',
                    'admin_comment', 'eth_balance', 'tokens_balance_eth',
                    'address_turnover', 'related_turnover', 'tokens_count',
                    'potential', 'utm_source', 'category_names')
    search_fields = ('sending_address', 'email', 'admin_comment',
                     'user_comment')
    raw_id_fields = ('users', 'orders', 'referral_code')
