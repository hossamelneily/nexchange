import django.contrib.auth.views as auth_views
from django.conf.urls import url

from accounts import views
from accounts.forms import LoginForm

account_urls = [
    url(r'^register$', views.user_registration,
        name='accounts.register'),

    url(r'^authenticate/$', views.user_by_phone,
        name='accounts.user_by_phone'),

    url(r'^resend_sms/$', views.resend_sms,
        name='accounts.resend_sms'),

    url(r'^verify_phone/$',
        views.verify_phone,
        name='accounts.verify_phone'),
    url(r'^profile$', views.UserUpdateView.as_view(),
        name='accounts.user_profile'),

    url(r'^create_withdraw_address/$',
        views.create_withdraw_address,
        name='accounts.create_withdraw_address'),

    url(r'^login', auth_views.login,
        {'template_name': 'accounts/user_login.html',
         'authentication_form': LoginForm},
        name='accounts.login'),
    url(r'^logout$', auth_views.logout,
        {'next_page': '/'},
        name='accounts.logout'),
    # asking for passwd reset
    url(r'^password/reset/$', auth_views.password_reset,
        {'post_reset_redirect': '/accounts/password/reset/done/',
         'template_name': 'accounts/password_reset.html',
         'email_template_name': 'accounts/password_reset_email.html'},
        name="accounts.password_reset"),
    # passwd reset e-mail sent
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        {'template_name': 'accounts/password_reset_done.html'}),
    # paswd reset url with sent via e-mail
    url(r'^password/reset/(?P<uidb64>[0-9A-Za-z_-]+)/\
        (?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm, {
            'post_reset_redirect': '/accounts/password/done/',
            'template_name': 'accounts/password_reset_confirm.html'},
        name='accounts.password_reset_confirm'),
    # after saved the new passwd
    url(r'^password/done/$', auth_views.password_reset_complete,
        {'template_name': 'accounts/password_reset_complete.html'}),
]
