from django.contrib import admin

from orders.models import Order


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ("price",)


admin.site.register(Order, OrderAdmin)
