from django.conf import settings
from accounts.utils import _create_anonymous_user
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework_extensions.etag.mixins import (
    ReadOnlyETAGMixin
)
from rest_framework_extensions.cache.mixins import (
    CacheResponseMixin
)
from referrals.middleware import ReferralMiddleWare
from oauth2_provider.models import Application, AccessToken
from oauthlib.common import generate_token
from datetime import timedelta
from django.utils import timezone

referral_middleware = ReferralMiddleWare()


class OrderPagination(PageNumberPagination):
    page_size = settings.RECENT_ORDERS_LENGTH
    page_size_query_param = 'page_size'


class BaseOrderListViewSet(viewsets.ModelViewSet,
                           ReadOnlyETAGMixin, CacheResponseMixin):
    permission_classes = ()
    lookup_field = 'unique_reference'
    pagination_class = OrderPagination
    http_method_names = ['get', 'post']

    def get_queryset(self, filters=None, only_public=True, **kwargs):
        self.queryset = self.model_class.objects.all()
        pair = self.request.query_params.get('pair', None)
        if pair is not None:
            self.queryset = self.queryset.filter(pair__name=pair)
        status = self.request.query_params.get('status', None)
        if status is not None:
            try:
                self.queryset = self.queryset.filter(status=status)
            except ValueError:
                self.queryset = self.queryset.none()
        return super(BaseOrderListViewSet, self).get_queryset()

    def _create_bearer_token(self, user):
        app, created = Application.objects.get_or_create(
            user=user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
            name=user.username
        )
        expires_in = settings.ACCESS_TOKEN_EXPIRE_SECONDS
        expires = timezone.now() + timedelta(seconds=expires_in)
        token = AccessToken(
            user=user,
            token=generate_token(),
            application=app,
            expires=expires
        )
        token.save()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            _create_anonymous_user(self.request)
            referral_middleware.process_request(self.request)
            self._create_bearer_token(self.request.user)
        serializer.save(user=self.request.user)

        return super(BaseOrderListViewSet, self).perform_create(serializer)
