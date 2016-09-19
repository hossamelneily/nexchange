from rest_framework.routers import SimpleRouter
from referrals.views import ReferralViewSet

router = SimpleRouter()
router.register(r'referrals', ReferralViewSet, base_name='referrals')
referrals_api_patterns = router.urls
