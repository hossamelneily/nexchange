from django.contrib import admin

from .models import Program, Referral, ReferralCode


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    search_fields = ('code', 'user__username')
    list_display = ('code', 'user')
    autocomplete_fields = ('user',)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    autocomplete_fields = ('currency',)


@admin.register(Referral)
class Referraldmin(admin.ModelAdmin):
    search_fields = ('code__code', 'referee__username', 'code__user__username')
    list_display = ('code', 'referee', 'turnover', 'revenue', 'orders')
    autocomplete_fields = ('code', 'referee')
