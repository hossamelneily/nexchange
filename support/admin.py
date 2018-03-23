from django.contrib import admin

from .models import Support


class SupportAdmin(admin.ModelAdmin):
    list_display = ['unique_reference', 'name', 'user', 'created_on',
                    'is_resolved']
    list_filter = ('is_resolved',)
    search_fields = ['user__username', ]
    readonly_fields = ['user', 'order', 'unique_reference', 'name', 'email',
                       'telephone', 'subject', 'message',
                       'frontend_order_links', 'backend_order_links']

    def _generate_order_links(self, obj, url):
        res = ''
        for order in obj.user_orders:
            res += '<a href="{url}{ref}/">{ref}</a> '.format(
                ref=order.unique_reference,
                url=url
            )
        return res

    def frontend_order_links(self, obj):
        return self._generate_order_links(obj, 'https://n.exchange/order/')

    def backend_order_links(self, obj):
        return self._generate_order_links(
            obj, 'https://api.nexchange.io/en/api/v1/orders/'
        )

    frontend_order_links.allow_tags = True
    backend_order_links.allow_tags = True


admin.site.register(Support, SupportAdmin)
admin.autodiscover()
