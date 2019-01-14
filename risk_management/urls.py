from rest_framework.routers import SimpleRouter

from risk_management.api_views import PNLListViewSet, PNLSheetViewSet

router = SimpleRouter()

router.register(r'risk_management/pnl', PNLListViewSet,
                basename='risk_management')
router.register(r'risk_management/pnl_sheet', PNLSheetViewSet,
                basename='risk_management')

risk_management_api_patterns = router.urls
