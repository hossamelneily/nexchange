from django.urls import path
from rest_framework.routers import SimpleRouter

from referrals.views import ReferralViewSet, referrals, ReferralCodeCreateView

router = SimpleRouter()
router.register(r'referrals', ReferralViewSet, basename='referrals')
referrals_api_patterns = router.urls

referral_urls = [
    path('', referrals, name='referrals.main'),
    path('code/new/', ReferralCodeCreateView.as_view(),
         name='referrals.code_new')
]
