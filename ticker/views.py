from rest_framework import viewsets
from rest_framework.response import Response

from core.common.views import DateFilterViewSet
from ticker.models import Price
from ticker.serializers import PriceSerializer


class LastPricesViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Price.objects.filter().order_by('-id')[:2]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(DateFilterViewSet):
    serializer_class = PriceSerializer

    def get_queryset(self):
        self.queryset = Price.objects
        return super(PriceHistoryViewSet, self).get_queryset()
