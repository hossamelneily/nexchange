from django.urls import path

from payments import views

payment_urls = [
    path('safe_charge/dmn/listen', views.SafeChargeListenView.as_view(),
         name='payments.listen_safe_charge'),
]
