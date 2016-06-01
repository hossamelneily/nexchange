"""nexchange URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
import django.contrib.auth.views as auth_views
import core.views
from core.models import Currency, Profile, Order, SmsToken
from core.forms import LoginForm
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from ticker.urls import api_patterns
# todo: move to admin.py
admin.site.register(Currency)
admin.site.register(Profile)
admin.site.register(Order)
admin.site.register(SmsToken)

urlpatterns = i18n_patterns(
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^$', core.views.add_order, name='core.order_add'),
    url(r'^info/$', core.views.main, name='main'),
    url(r'^order/$',  core.views.index_order, name='core.order'),
    url(r'^order/ajax/$',  core.views.ajax_order, name='core.ajax_order'),
    url(r'^order/update_withdraw_address/(?P<pk>[\d]+)/$',
        core.views.update_withdraw_address,
        name='core.update_withdraw_address'),
    url(r'^order/payment_confirmation/(?P<pk>[\d]+)/$',
        core.views.payment_confirmation,
        name='core.payment_confirmation'),
    url(r'^profile/add$', core.views.user_registration,
        name='core.user_registration'),
    url(r'^profile/resendSMS/$',  core.views.resend_sms,
        name='core.resend_sms'),
    url(r'^profile/add$', core.views.user_registration,
        name='core.user_registration'),
    url(r'^profile/resendSMS/$',  core.views.resend_sms, name='core.resend_sms'),
    url(r'^profile/verifyPhone/$',
        core.views.verify_phone, name='core.verify_phone'),
    url(r'^profile/(?P<slug>[-\+\w\d]+)/$',
        core.views.UserUpdateView.as_view(), name='core.user_profile'),

    url(r'^accounts/login/$', auth_views.login,
        {'template_name': 'core/user_login.html',
            'authentication_form': LoginForm},
        name='accounts.login'),
    url(r'^accounts/logout/$', auth_views.logout,
        {'next_page': '/'},
        name='accounts.logout'),
    # asking for passwd reset
    url(r'^accounts/password/reset/$', auth_views.password_reset,
        {'post_reset_redirect': '/accounts/password/reset/done/'},
        name="accounts.password_reset"),
    # passwd reset e-mail sent
    url(r'^accounts/password/reset/done/$', auth_views.password_reset_done),
    # paswd reset url with sent via e-mail
    url(r'^accounts/password/reset/(?P<uidb64>[0-9A-Za-z_-]+)/\
        (?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm, {
            'post_reset_redirect': '/accounts/password/done/'},
        name='accounts.password_reset_confirm'),
    # after saved the new passwd
    url(r'^accounts/password/done/$', auth_views.password_reset_complete),
    url(r'^api/v1/', include(api_patterns)),
    url(r'^kraken/trades/$', core.views.k_trades_history, name='core.k_trades_history'),
    url(r'^api/v1/phone$', core.views.user_by_phone, name='core.user_by_phone'),
    url(r'^api/v1/menu', core.views.ajax_menu, name='core.menu'),
    url(r'^api/v1/breadcrumbs', core.views.ajax_crumbs, name='core.breadcrumbs'),



)