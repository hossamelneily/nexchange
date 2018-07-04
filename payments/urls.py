from django.conf.urls import url

from payments import views

payment_urls = [
    url(r'^safe_charge/dmn/listen$', views.SafeChargeListenView.as_view(),
        name='payments.listen_safe_charge'),
]
