from rest_framework.routers import SimpleRouter
from .api_views import SubscriptionViewSet

router = SimpleRouter()
router.register(r'subscriptions', SubscriptionViewSet, base_name='SubscriptionViewSet')

ico_api_patterns = router.urls
