from rest_framework import viewsets
from rest_framework.response import Response
from ticker.serializers import PriceSerializer
from ticker.models import Price
import datetime


class LastPricesViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = Price.objects.filter().order_by('-id')[:2]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(viewsets.ViewSet):
    def list(self, request):
        day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        queryset = Price.objects.filter(created_on__gte=day_ago)
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)

