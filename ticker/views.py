from django.conf import settings
from rest_framework.response import Response

from core.common.views import DateFilterViewSet, DataPointsFilterViewSet
from ticker.models import Price
from ticker.serializers import PriceSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin, ReadOnlyETAGMixin
)


class LastPricesViewSet(ReadOnlyCacheResponseAndETAGMixin,
                        DateFilterViewSet):

    @method_decorator(cache_page(settings.PRICE_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(LastPricesViewSet, self).dispatch(*args, **kwargs)

    def list(self, request, pair=None):
        if pair is not None:
            pair = pair.upper()
        queryset = Price.objects.filter(
            pair__name=pair,
        ).order_by('-id')[:1]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(ReadOnlyETAGMixin,
                          DataPointsFilterViewSet):
    serializer_class = PriceSerializer

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Price.objects
        if filters is None:
            filters = {}
        filters['pair__name'] = self.kwargs['pair'].upper()
        res = super(PriceHistoryViewSet, self).get_queryset(filters=filters)

        return res
