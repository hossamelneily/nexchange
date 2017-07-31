from rest_framework.routers import SimpleRouter
from core import api_views

router = SimpleRouter()
router.register(r'currency', api_views.CurrencyViewSet,
                base_name='currency')

core_api_patterns = router.urls