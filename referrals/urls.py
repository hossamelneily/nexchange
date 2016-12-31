from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from referrals.views import ReferralViewSet, referrals

router = SimpleRouter()
router.register(r'referrals', ReferralViewSet, base_name='referrals')
referrals_api_patterns = router.urls

referral_urls = [
    url(r'', referrals, name='referrals.main')
]
