from django.conf.urls.i18n import i18n_patterns
from django.conf.urls import url
from payments import views

payment_patterns = i18n_patterns(
    url('success', views.payment_success)
)
