import datetime

from rest_framework import generics
from random import choice
from rest_framework import viewsets
from nexchange.permissions import NoUpdatePermission, OwnerOnlyPermission


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
        if 'data_points' in params:
            original_len = len(res)

            data_points = int(self.request.query_params.get('data_points'))
            if data_points < original_len:
                pks = []
                step = original_len / data_points
                number = 0
                count = 0
                while number < original_len:
                    pks.append(res[int(number)].pk)
                    number += step
                    count += 1
                if count - data_points == 1:
                    ticker_to_remove = choice(pks)
                    pks.remove(ticker_to_remove)
                res = self.queryset.filter(pk__in=pks).order_by('id')
        return res


class UserResourceViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission, OwnerOnlyPermission,)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        return super(UserResourceViewSet, self).perform_create(serializer)
