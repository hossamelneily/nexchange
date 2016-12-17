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
import core.views
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from ticker.urls import ticker_api_patterns
from payments.urls import payment_urls
from referrals.urls import referrals_api_patterns, referral_urls
from orders.urls import order_urls
from accounts.urls import account_urls
from articles.urls import article_urls
from django.conf import settings
from django.conf.urls.static import static
import os
from django.views.i18n import javascript_catalog


js_info_dict = {
    'domain': 'djangojs',
    'packages': ('nexchange',),
}


api_patterns = ticker_api_patterns + referrals_api_patterns

urlpatterns = i18n_patterns(
    url(r'^admin/', admin.site.urls),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', javascript_catalog, js_info_dict),
    url(r'^$', core.views.main, name='main'),
    url(r'^orders/', include(order_urls)),
    url(r'^accounts/', include(account_urls)),
    url(r'^payments/', include(payment_urls)),
    url(r'^referrals/', include(referral_urls)),
    url(r'^articles/', include(article_urls)),

    url(r'^api/v1/', include(api_patterns)),
    url(r'^api/v1/menu', core.views.ajax_menu, name='core.menu'),
    url(r'^api/v1/breadcrumbs', core.views.ajax_crumbs,
        name='core.breadcrumbs'),
    url(r'session_security/', include('session_security.urls')),
)

if settings.DEBUG:
    # pragma: no cover
    urlpatterns += static('/cover', document_root=os.path.join(
        settings.BASE_DIR, 'cover'))

    # Debug toolbar urls
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
