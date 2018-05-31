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
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.views.i18n import javascript_catalog
from django_otp.admin import OTPAdminSite
from django.views.static import serve
from django.http import HttpResponseForbidden
import re


import core.views
from core.urls import core_api_patterns
from accounts.urls import account_urls, account_api_patterns
from articles.urls import article_urls
from orders.urls import order_urls, order_api_patterns
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
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', javascript_catalog, js_info_dict,
        name='nexchange.javascript_catalog'),
    url(r'^$', core.views.main, name='main'),
    url(r'^orders/', include(order_urls)),
    url(r'^accounts/', include(account_urls)),
    url(r'^payments/', include(payment_urls)),
    url(r'^referrals/', include(referral_urls)),
    url(r'^articles/', include(article_urls)),
    url(r'^support/', include(support_urls)),
    url(r'^verification/', include(verification_urls)),

    url(r'^api/v1/', include(api_patterns)),
    url(r'^api/v1/menu', core.views.ajax_menu, name='core.menu'),
    url(r'^api/v1/get_price/(?P<pair_name>[^/.]+)/$', PriceView.as_view(),
        name='get_price'),
    url(r'^api/v1/oAuth2/', include('oauth2_provider.urls',
                                    namespace='oauth2_provider')),
    url(r'^api/v1/breadcrumbs', core.views.ajax_crumbs,
        name='core.breadcrumbs'),
    url(r'session_security/', include('session_security.urls')),
)
# OAUTH outside i18n so that we do not need to explisitly define every
# redirect address in social apps
urlpatterns.append(
    url(r'oauth/', include('social_django.urls', namespace='oauth.social'))
)


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    return serve(request, path, document_root, show_indexes)


# protected_media to test
urlpatterns.append(
    url(r'^%s(?P<path>.*)$' % re.escape('/protected_media/'.lstrip('/')),
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
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
