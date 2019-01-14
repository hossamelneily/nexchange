from rest_framework.routers import SimpleRouter

from django.urls import path
from support.views import SupportView, ThanksView
from support.api_views import SupportViewSet

router = SimpleRouter()

router.register(r'support', SupportViewSet, basename='support')

support_api_patterns = router.urls

support_urls = [
    path('', SupportView.as_view(), name='support_urls'),
    path('thanks/', ThanksView.as_view()),
]
