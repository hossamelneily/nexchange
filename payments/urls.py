from django.conf.urls import url

from payments import views

payment_urls = [
    url(r'^success/(?P<provider>.+)/$', views.payment_success,
        name='payments.success'),
    url(r'^error/(?P<provider>.+)/$', views.payment_failure,
        name='payments.failure'),
    url(r'^retry/(?P<provider>.+)/$', views.payment_retry,
        name='payments.retry'),
    url(r'^info/(?P<provider>.+)/$', views.payment_info,
        name='payments.info'),
    url(r'^options/$',
        views.payment_type,
        name='payments.options'),
    url(r'^payeer/status$', views.payeer_status,
        name='payments.payeer.status'),
]
