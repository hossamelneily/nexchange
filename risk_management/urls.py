from rest_framework.routers import SimpleRouter

from django.conf.urls import url
from risk_management.api_views import PNLListViewSet, PNLSheetViewSet

router = SimpleRouter()

router.register(r'risk_management/pnl', PNLListViewSet, base_name='risk_management')
router.register(r'risk_management/pnl_sheet', PNLSheetViewSet, base_name='risk_management')

risk_management_api_patterns = router.urls
