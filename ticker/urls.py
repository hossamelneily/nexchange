from rest_framework.routers import DefaultRouter
from ticker.views import LastPricesViewSet, PriceHistoryViewSet

router = DefaultRouter()
router.register(r'price/latest', LastPricesViewSet, base_name='latest')
router.register(r'price/history', PriceHistoryViewSet, base_name='history')
api_patterns = router.urls
