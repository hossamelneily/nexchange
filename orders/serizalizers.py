from rest_framework import serializers
from core.common.serializers import FlattenMixin
from core.serializers import NestedPairSerializer
from orders.models import Order

WRITABLE_FIELDS = ('amount_base', 'is_default_rule', 'unique_reference', 'amount_quote', 'pair')
READABLE_FIELDS = ('amount_quote', 'from_default_rule', 'unique_reference',)


class MetaOrder:
    model = Order
    fields = WRITABLE_FIELDS
    read_only_fields = READABLE_FIELDS


class MetaFlatOrder(MetaOrder):
    fields = MetaOrder.fields + READABLE_FIELDS
    flatten = [('pair', NestedPairSerializer)]


class OrderSerializer(serializers.ModelSerializer, FlattenMixin):
    class Meta(MetaFlatOrder):
        pass


class CreateOrderSerializer(OrderSerializer):
    class Meta(MetaOrder):
        fields = MetaOrder.fields + ('pair',)
