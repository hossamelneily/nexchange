from rest_framework.routers import SimpleRouter

from django.conf.urls import url
from orders.api_views import OrderListViewSet
from orders import views

router = SimpleRouter()

router.register(r'orders', OrderListViewSet, base_name='orders')

order_api_patterns = router.urls


order_urls = [
    url(r'^$', views.orders_list, name='orders.orders_list'),
    url(r'^buy_bitcoin/(?P<pair>[A-Za-z_-]+)/$',
        views.add_order, name='orders.add_order'),
    url(r'^buy_bitcoin/$',
        views.add_order, name='orders.add_order'),
    url(r'^sell_bitcoin/(?P<pair>[A-Za-z_-]+)/$',
        views.add_order_sell,
        name='orders.add_order_sell'),
    url(r'^sell_bitcoin/$',
        views.add_order_sell,
        name='orders.add_order_sell'),

    url(r'^add_order/$', views.ajax_order, name='orders.ajax_order'),
    url(r'^update_withdraw_address/(?P<pk>[\d]+)/$',
        views.update_withdraw_address,
        name='orders.update_withdraw_address'),
    url(r'^confirm_payment/(?P<pk>[\d]+)/$',
        views.payment_confirmation,
        name='orders.confirm_payment'),
]
