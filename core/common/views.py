import datetime

from rest_framework import generics, viewsets
from random import choice
from time import time
from nexchange.utils import get_nexchange_logger


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

    logger = get_nexchange_logger('Data Points Filter')

    def get_queryset(self, filters=None):
        params = self.request.query_params

        before_db_query = time()
        res = super(DataPointsFilterViewSet, self).get_queryset(
            filters=filters
        )
        after_db_query = time()
        if 'data_points' in params:
            original_len = len(res)

            data_points = int(self.request.query_params.get('data_points'))
            a1 = a2 = a3 = 0.0
            if data_points < original_len:
                pks = []
                step = len(res) / data_points
                number = 0
                a1 = time()
                while number < original_len:
                    pks.append(res[int(number)].pk)
                    number += step
                a2 = time()
                if len(pks) - data_points == 1:
                    ticker_to_remove = choice(pks)
                    pks.remove(ticker_to_remove)
                a3 = time()
                res = self.queryset.filter(pk__in=pks).order_by('id')
        after_points_filter = time()
        message = (
            'Data points request({}). time filter time: {}. Data points '
            'filter time: {} = {} + {} + {} + {}'.format(
                self.request.query_params,
                after_db_query - before_db_query,
                after_points_filter - after_db_query,
                a1 - after_db_query,
                a2 - a1,
                a3 - a2,
                after_points_filter - a3
            )
        )
        print(message)
        self.logger.info(message)
        return res
