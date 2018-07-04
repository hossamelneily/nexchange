from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from verification.views import views
from .api_views import VerificationViewSet

router = SimpleRouter()

router.register(r'kyc', VerificationViewSet, base_name='kyc')

kyc_api_patterns = router.urls

verification_urls = [
    url(r'^download/(?P<file_name>.*)/$', views.download,
        name='verification.download'),
]
