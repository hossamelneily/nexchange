from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import generics
from ticker.serializers import PriceSerializer
from ticker.models import Price
import datetime
from nexchange.settings import DEFAULT_HOUR_RANGE


class LastPricesViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = Price.objects.filter().order_by('-id')[:2]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(viewsets.ViewSetMixin, generics.ListAPIView):
    serializer_class = PriceSerializer

    def get_queryset(self, *args, **kwargs):
        hours = self.request.query_params.get('hours', DEFAULT_HOUR_RANGE)
        seconds = float(hours) * 3600
        relevant = datetime.datetime.now() \
            - datetime.timedelta(seconds=seconds)
        queryset = Price.objects.\
            filter(created_on__gte=relevant).order_by('id')
        return queryset
