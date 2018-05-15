from risk_management.models import PNLSheet, PNL
from risk_management.serializers import PNLSheetSerializer, \
    PNLSerializer
from nexchange.permissions import NoUpdatePermission
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination


class PNLPagination(PageNumberPagination):
    page_size = settings.RECENT_PNL_LENGTH
    page_size_query_param = 'page_size'


class PNLSheetViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission,)
    model_class = PNLSheet
    serializer_class = PNLSheetSerializer
    pagination_class = PNLPagination
    http_method_names = ['get']

    @method_decorator(cache_page(settings.PNL_SHEET_CACHE_LIFETIME))
    def list(self, request, *args, **kwargs):
        return super(PNLSheetViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = PNLSheet.objects.all()
        return super(PNLSheetViewSet, self).get_queryset()


class PNLListViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission,)
    model_class = PNL
    lookup_field = 'pair__name'
    serializer_class = PNLSerializer
    pagination_class = PNLPagination
    http_method_names = ['get']

    @method_decorator(cache_page(settings.PNL_CACHE_LIFETIME))
    def list(self, request, *args, **kwargs):
        return super(PNLListViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = PNL.objects.all()
        return super(PNLListViewSet, self).get_queryset()
