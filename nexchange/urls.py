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
import os

from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog
from django.conf.urls.static import static
from django.contrib import admin
from django_otp.admin import OTPAdminSite
from django.views.static import serve
from django.http import HttpResponseForbidden
import re


import core.views
from core.urls import core_api_patterns
from accounts.urls import account_urls, account_api_patterns
from articles.urls import article_urls
from orders.urls import order_api_patterns
from risk_management.urls import risk_management_api_patterns
from orders.api_views import PriceView
from payments.urls import payment_urls
from referrals.urls import referral_urls, referrals_api_patterns
from support.urls import support_urls, support_api_patterns
from ticker.urls import ticker_api_patterns
from verification.urls import verification_urls, kyc_api_patterns
from ico.urls import ico_api_patterns
from django.contrib.auth.decorators import login_required

if not settings.DEBUG:
    admin.site.__class__ = OTPAdminSite


js_info_dict = {
    'domain': 'djangojs',
    'packages': (
        'nexchange',
        'core',
        'orders',
        'payments',
        'referrals',
        'ticker'
    ),
}


api_patterns = ticker_api_patterns + referrals_api_patterns \
    + order_api_patterns + account_api_patterns + \
    core_api_patterns + support_api_patterns + kyc_api_patterns + \
    risk_management_api_patterns + ico_api_patterns


urlpatterns = i18n_patterns(
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(),
         name='nexchange.javascript_catalog'),
    path('', core.views.main, name='main'),
    path('accounts/', include(account_urls)),
    path('payments/', include(payment_urls)),
    path('referrals/', include(referral_urls)),
    path('articles/', include(article_urls)),
    path('support/', include(support_urls)),
    path('verification/', include(verification_urls)),
    path('newsletter/', include('newsletter.urls')),

    path('api/v1/', include(api_patterns)),
    path('api/v1/menu', core.views.ajax_menu, name='core.menu'),
    re_path(r'^api/v1/get_price/(?P<pair_name>[^/.]+)/$', PriceView.as_view(),
            name='get_price'),
    path('api/v1/oAuth2/', include('oauth2_provider.urls',
                                   namespace='oauth2_provider')),
    path('api/v1/breadcrumbs', core.views.ajax_crumbs,
         name='core.breadcrumbs'),
    path('session_security/', include('session_security.urls')),
    re_path(r'^_nested_admin/', include('nested_admin.urls')),
)
# OAUTH outside i18n so that we do not need to explisitly define every
# redirect address in social apps
urlpatterns.append(
    path('oauth/', include('social_django.urls', namespace='oauth.social'))
)


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    return serve(request, path, document_root, show_indexes)


# protected_media to test
urlpatterns.append(
    re_path(r'^%s(?P<path>.*)$' % re.escape('/protected_media/'.lstrip('/')),
            protected_serve,
            kwargs={'document_root': settings.MEDIA_ROOT})
)

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static('/cover', document_root=os.path.join(
        settings.BASE_DIR, 'cover'))

    # Debug toolbar urls
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
