from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('email', 'sending_address', )

    def create(self, validated_data):
        try:
            instance = \
                Subscription.objects.filter(**validated_data).latest('id')
        except Subscription.DoesNotExist:
            instance = Subscription.objects.create(**validated_data)

        return instance
