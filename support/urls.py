from rest_framework.routers import SimpleRouter

from django.conf.urls import url
from support.views import SupportView, ThanksView
from support.api_views import SupportViewSet

router = SimpleRouter()

router.register(r'support', SupportViewSet, base_name='support')

support_api_patterns = router.urls

support_urls = [
    url(r'^$', SupportView.as_view(), name='support_urls'),
    url(r'^thanks/$', ThanksView.as_view()),
]
