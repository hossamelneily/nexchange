from orders.serializers import MetaFlatOrder, OrderSerializer
from core.common.serializers import PartialModelSerializer
from django.contrib.auth.models import User
from accounts.models import Profile
from rest_framework.validators import UniqueValidator
from rest_framework import serializers
from phonenumber_field.phonenumber import to_python


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair',)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('phone',)


class UserSerializer(PartialModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    phone = serializers.CharField(source='profile.phone', required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone')

    def update(self, instance, validated_data):
        phone = validated_data.pop('profile', {}).pop('phone', None)
        if phone and to_python(phone).is_valid():
            profile = instance.profile
            profile.phone = phone
            profile.save()
        return super(UserSerializer, self).update(instance, validated_data)
