from rest_framework import viewsets
from nexchange.permissions import NoUpdatePermission
from core.models import Currency, Pair
from core.serializers import CurrencySerializer, PairSerializer


class CurrencyViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission,)
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()
    lookup_field = 'code'


class PairViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission,)
    serializer_class = PairSerializer
    queryset = Pair.objects.all()
    lookup_field = 'name'
