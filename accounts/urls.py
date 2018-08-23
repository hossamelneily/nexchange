from rest_framework.routers import SimpleRouter

import django.contrib.auth.views as auth_views
from django.urls import re_path, path

from accounts import views, api_views
from accounts.forms import LoginForm

router = SimpleRouter()
router.register(r'users/me/orders', api_views.UserOrderListViewSet,
                base_name='orders')
router.register(r'users/me/addresses', api_views.UserAddressViewSet,
                base_name='addresses')
router.register(r'users', api_views.UserViewSet,
                base_name='users')
account_api_patterns = router.urls

account_urls = [
    path('register', views.user_registration,
         name='accounts.register'),

    path('authenticate/', views.user_get_or_create,
         name='accounts.user_get_or_create'),

    path('resend_sms/', views.resend_sms,
         name='accounts.resend_sms'),

    path('verify_user/',
         views.verify_user,
         name='accounts.verify_user'),

    path('create_anonymous_user/',
         views.create_anonymous_user,
         name='accounts.create_anonymous_user'),

    path('login_anonymous/',
         views.AnonymousLoginView.as_view(),
         name='accounts.login_anonymous'),

    path('profile', views.UserUpdateView.as_view(),
         name='accounts.user_profile'),

    path('profile/referrals/', views.ReferralUpdateView.as_view(),
         name='accounts.referral_update'),

    re_path(r'^create_withdraw_address/(?P<order_pk>[\d]+)/$',
            views.create_withdraw_address,
            name='accounts.create_withdraw_address'),

    re_path(r'^login', auth_views.login,
            {'template_name': 'accounts/user_login.html',
             'authentication_form': LoginForm},
            name='accounts.login'),
    re_path(r'^logout', auth_views.logout,
            {'next_page': '/'},
            name='accounts.logout'),
    # asking for passwd reset
    re_path(r'^password/reset/', auth_views.password_reset,
            {'post_reset_redirect': '/accounts/password/reset/done/',
             'template_name': 'accounts/password_reset.html',
             'email_template_name': 'accounts/password_reset_email.html'},
            name="accounts.password_reset"),
    # passwd reset e-mail sent
    path('password/reset/done/',
         auth_views.password_reset_done,
         {'template_name': 'accounts/password_reset_done.html'}),
    # paswd reset url with sent via e-mail
    re_path(r'^password/reset/(?P<uidb64>[0-9A-Za-z_-]+)/\
            (?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            auth_views.password_reset_confirm, {
             'post_reset_redirect': '/accounts/password/done/',
             'template_name': 'accounts/password_reset_confirm.html'
            },
            name='accounts.password_reset_confirm'),
    # after saved the new passwd
    path('password/done/', auth_views.password_reset_complete,
         {'template_name': 'accounts/password_reset_complete.html'}),
    path('password/change/', views.change_password,
         name='accounts.change_password'),
]
