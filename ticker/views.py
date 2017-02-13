from rest_framework.response import Response

from core.common.views import DateFilterViewSet
from ticker.models import Price
from ticker.serializers import PriceSerializer
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)


class LastPricesViewSet(ReadOnlyCacheResponseAndETAGMixin,
                        DateFilterViewSet):
    def list(self, request, pair=None):
        queryset = Price.objects.filter(
            pair__name=pair,
        ).order_by('-id')[:1]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(ReadOnlyCacheResponseAndETAGMixin,
                          DateFilterViewSet):
    serializer_class = PriceSerializer

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Price.objects
        if filters is None:
            filters = {}
        filters['pair__name'] = self.kwargs['pair']
        return super(PriceHistoryViewSet, self).get_queryset(filters=filters)
