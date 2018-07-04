from rest_framework.routers import SimpleRouter

from orders.api_views import OrderListViewSet, VolumeViewSet,\
    TradeHistoryViewSet

router = SimpleRouter()

router.register(r'orders', OrderListViewSet, base_name='orders')
router.register(r'volume', VolumeViewSet, base_name='orders')
router.register(r'trade_history', TradeHistoryViewSet,
                base_name='trade_history')

order_api_patterns = router.urls
