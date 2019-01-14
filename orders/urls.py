from rest_framework.routers import SimpleRouter

from orders.api_views import OrderListViewSet, VolumeViewSet,\
    TradeHistoryViewSet, LimitOrderListViewSet, StandardTickerViewSet

router = SimpleRouter()

router.register(r'orders', OrderListViewSet, basename='orders')
router.register(r'volume', VolumeViewSet, basename='volume')
router.register(r'ticker', StandardTickerViewSet, basename='ticker')
router.register(r'trade_history', TradeHistoryViewSet,
                basename='trade_history')
router.register(r'limit_order', LimitOrderListViewSet, basename='limit_order')

order_api_patterns = router.urls
