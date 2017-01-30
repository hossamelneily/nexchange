from rest_framework import viewsets
from rest_framework.response import Response

from core.common.views import DateFilterViewSet
from ticker.models import Price
from ticker.serializers import PriceSerializer
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)


class LastPricesViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request):
        queryset = Price.objects.filter().order_by('-id')[:2]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(ReadOnlyCacheResponseAndETAGMixin,
                          DateFilterViewSet):
    serializer_class = PriceSerializer

    def get_queryset(self):
        self.queryset = Price.objects
        return super(PriceHistoryViewSet, self).get_queryset()
