import datetime

from rest_framework import generics, viewsets
from random import choice


class DateFilterViewSet(viewsets.ViewSetMixin, generics.ListAPIView):

    def __init__(self, *args, **kwargs):
        self.queryset = None
        super(DateFilterViewSet, self).__init__(*args, **kwargs)

    def get_queryset(self, filters=None):
        if filters is None:
            filters = {}
        params = self.request.query_params

        if 'hours' in params:
            hours = self.request.query_params.get('hours')
            seconds = float(hours) * 3600
            relevant = datetime.datetime.now() - \
                datetime.timedelta(seconds=seconds)
            filters['created_on__gte'] = relevant
        elif 'date' in params:
            # Todo: Add this functionality
            # Todo: Add start and end func
            raise NotImplementedError()
        if self.queryset is not None:
            return self.queryset.filter(**filters).order_by('id')
        else:
            return []


class DataPointsFilterViewSet(DateFilterViewSet):

    def get_queryset(self, filters=None):
        params = self.request.query_params

        res = super(DataPointsFilterViewSet, self).get_queryset(
            filters=filters
        )
        if len(res) > 0:
            if 'data_points' in params:

                data_points = int(self.request.query_params.get('data_points'))
                pks = []
                step = len(res) / data_points
                number = 0
                while number < len(res):
                    pks.append(res[int(number)].pk)
                    number += step
                if len(pks) - data_points == 1:
                    ticker_to_remove = choice(pks)
                    pks.remove(ticker_to_remove)
                return self.queryset.filter(pk__in=pks).order_by('id')
        return res
