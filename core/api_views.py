from rest_framework import viewsets
from nexchange.permissions import NoUpdatePermission
from core.models import Currency
from core.serializers import CurrencySerializer


class CurrencyViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission,)
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()
    lookup_field = 'code'

