from rest_framework.routers import SimpleRouter

from orders.api_views import OrderListViewSet, VolumeViewSet,\
    TradeHistoryViewSet, LimitOrderListViewSet, StandardTickerViewSet

router = SimpleRouter()

router.register(r'orders', OrderListViewSet, base_name='orders')
router.register(r'volume', VolumeViewSet, base_name='orders')
router.register(r'ticker', StandardTickerViewSet, base_name='ticker')
router.register(r'trade_history', TradeHistoryViewSet,
                base_name='trade_history')
router.register(r'limit_order', LimitOrderListViewSet, base_name='limit_order')

order_api_patterns = router.urls
