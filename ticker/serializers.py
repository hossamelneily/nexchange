from rest_framework import serializers
from ticker.models import Price


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ('price_rub', 'price_usd', 'rate', 'type', 'created_on')