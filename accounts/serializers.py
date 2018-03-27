from orders.serializers import MetaFlatOrder, OrderSerializer
from core.common.serializers import PartialModelSerializer
from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from rest_framework import serializers


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair',)


class UserSerializer(PartialModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ('username', 'email',)
