from django.conf import settings
from orders.models import Order
from orders.serializers import OrderSerializer, CreateOrderSerializer, \
    NestedPairSerializer, OrderDetailSerializer
from accounts.utils import _create_anonymous_user
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, never_cache
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException, \
    ValidationError as RestValidationError
from rest_framework import status
from collections import OrderedDict
from core.models import Pair
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from ticker.models import Price
from core.common.api_views import DateFilterViewSet
from referrals.middleware import ReferralMiddleWare
from oauth2_provider.models import Application, AccessToken
from oauthlib.common import generate_token
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import ugettext as _

referral_middleware = ReferralMiddleWare()


class OrderPagination(PageNumberPagination):
    page_size = settings.RECENT_ORDERS_LENGTH
    page_size_query_param = 'page_size'


class OrderListViewSet(viewsets.ModelViewSet,
                       ReadOnlyCacheResponseAndETAGMixin):
    permission_classes = ()
    model_class = Order
    lookup_field = 'unique_reference'
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    http_method_names = ['get', 'post']

    @method_decorator(cache_page(settings.ORDER_CACHE_LIFETIME))
    def list(self, request, *args, **kwargs):
        return super(OrderListViewSet, self).list(request, *args, **kwargs)

    @never_cache
    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = OrderDetailSerializer
        return super(OrderListViewSet, self).retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer

        return super(OrderListViewSet, self).get_serializer_class()

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.all()
        return super(OrderListViewSet, self).get_queryset()

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

        return super(OrderListViewSet, self).perform_create(serializer)


class VolumeViewSet(ReadOnlyCacheResponseAndETAGMixin, DateFilterViewSet):

    model_class = Order
    http_method_names = ['get']

    @method_decorator(cache_page(settings.VOLUME_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(VolumeViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self, filters=None, **kwargs):
        if filters is None:
            filters = {}
        filters['status'] = Order.COMPLETED
        return super(VolumeViewSet, self).get_queryset(filters=filters,
                                                       **kwargs)

    def get_rate(self, currency):
        return Price.get_rate('BTC', currency)

    def list(self, request):
        params = self.request.query_params
        if 'hours' in params:
            hours = float(self.request.query_params.get('hours'))
        else:
            hours = 24
        queryset = self.get_queryset(hours=hours)
        data = OrderedDict({'hours': hours})
        volume_data = []
        pairs = Pair.objects.filter(disable_volume=False)
        total_base = total_quote = 0
        for pair in pairs:
            try:
                rate_base = self.get_rate(pair.base)
                rate_quote = self.get_rate(pair.quote)
                last_ask = Price.objects.filter(
                    pair=pair, market__is_main_market=True
                ).latest('id').rate
            except Price.DoesNotExist:
                continue
            volume = queryset.filter(pair=pair).aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            base_volume = volume['amount_base__sum']
            quote_volume = volume['amount_quote__sum']
            if base_volume is None:
                base_volume = Decimal('0.0')
            if quote_volume is None:
                quote_volume = Decimal('0.0')
            base_volume_btc = round(base_volume / rate_base, 8)
            quote_volume_btc = round(quote_volume / rate_quote, 8)
            total_base += base_volume_btc
            total_quote += quote_volume_btc
            pair_data = NestedPairSerializer(pair).data
            pair_data = OrderedDict({
                'base_volume': base_volume,
                'quote_volume': quote_volume,
                'base_volume_btc': base_volume_btc,
                'quote_volume_btc': quote_volume_btc,
                'last_ask': last_ask,
                'pair': pair_data
            })
            volume_data.append(pair_data)
        data.update({
            'total_volume': {
                'base_volume_btc': total_base,
                'quote_volume_btc': total_quote,
            }})
        data.update({'tradable_pairs': volume_data})

        data = OrderedDict(data)
        return Response(data)


class PriceView(APIView):

    PAIR_REQUIRED = APIException(detail=_('pair_name is required'))
    PAIR_REQUIRED.status_code = status.HTTP_400_BAD_REQUEST

    PAIR_DOES_NOT_EXIST = APIException(detail=_('pair does not exist'))
    PAIR_DOES_NOT_EXIST.status_code = status.HTTP_404_NOT_FOUND

    def _create_order_with_default_values(self, pair):
        base_maximal = pair.base.current_maximal_amount_to_sell
        base_minimal = pair.base.minimal_amount
        quote_maximal = pair.quote.maximal_amount
        quote_minimal = pair.quote.minimal_amount
        if pair.is_crypto:
            amount_quote = \
                quote_minimal * \
                settings.DEFAULT_CRYPTO_ORDER_DEPOSIT_AMOUNT_MULTIPLIER
            if amount_quote >= quote_maximal:
                amount_quote = (quote_maximal + quote_minimal) / Decimal('2')
        else:
            amount_quote = settings.DEFAULT_FIAT_ORDER_DEPOSIT_AMOUNT
        order = Order(pair=pair, amount_quote=amount_quote)
        order.calculate_base_from_quote()
        if all([not base_minimal <= order.amount_base <= base_maximal,
                base_maximal > base_minimal]):
            if order.amount_base > base_maximal:
                # return value between minimal and maximal possible
                # (closer to maximal to avoid minimal quote error)
                amount_base = \
                    (base_minimal + Decimal('4') * base_maximal) / Decimal('5')
            else:
                amount_base = base_minimal
            order = Order(pair=pair, amount_base=amount_base)
            order.calculate_quote_from_base()

        return order

    def _amount_to_decimal(self, amount_name):
        amount = self.request.GET.get(amount_name)
        if not amount:
            return
        try:
            return Decimal(amount)
        except InvalidOperation:
            return

    def _get(self, request, pair_name=None):
        amount_base = self._amount_to_decimal('amount_base')
        amount_quote = self._amount_to_decimal('amount_quote')
        if not pair_name:
            raise self.PAIR_REQUIRED
        try:
            pair = Pair.objects.get(name=pair_name)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            raise self.PAIR_DOES_NOT_EXIST
        if amount_base:
            amount_base = Decimal(amount_base)
            order = Order(pair=pair, amount_base=amount_base)
            order.calculate_quote_from_base()
        elif amount_quote:
            amount_quote = Decimal(amount_quote)
            order = Order(pair=pair, amount_quote=amount_quote)
            order.calculate_base_from_quote()
        else:
            order = self._create_order_with_default_values(pair)
        data = OrderedDict(
            {'amount_base': order.amount_base,
             'amount_quote': order.amount_quote})
        order._validate_order_amount()
        return Response(data)

    def get(self, request, pair_name=None):
        try:
            return self._get(request, pair_name=pair_name)
        except ValidationError as e:
            raise RestValidationError({'detail': e.message})
