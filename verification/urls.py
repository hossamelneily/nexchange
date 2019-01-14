from django.urls import re_path
from django.urls import path
from rest_framework.routers import SimpleRouter

from verification.views import views
from .api_views import VerificationViewSet

router = SimpleRouter()

router.register(r'kyc', VerificationViewSet, basename='kyc')

kyc_api_patterns = router.urls

verification_urls = [
    re_path(r'^download/(?P<file_name>.*)/$', views.download,
            name='verification.download'),
    path('idenfy/callback', views.IdenfyListenView.as_view(),
         name='verification.idenfy_callback'),
]
