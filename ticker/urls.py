from rest_framework.routers import SimpleRouter

from ticker.api_views import LastPricesViewSet, PriceHistoryViewSet,\
    BestChangeRateViewSet

router = SimpleRouter()
router.register(r'price/(?P<pair>[A-Za-z_-]+)/latest', LastPricesViewSet,
                base_name='latest')
router.register(r'price/(?P<pair>[A-Za-z_-]+)/history', PriceHistoryViewSet,
                base_name='history')
router.register(r'price_xml', BestChangeRateViewSet, base_name='price_xml')
ticker_api_patterns = router.urls
