from rest_framework.routers import SimpleRouter
from core import api_views

router = SimpleRouter()
router.register(r'currency', api_views.CurrencyViewSet,
                basename='currency')
router.register(r'pair', api_views.PairViewSet,
                basename='pair')

core_api_patterns = router.urls
