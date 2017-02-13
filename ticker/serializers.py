from rest_framework import serializers

from ticker.models import Price, Ticker


class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = ('ask', 'bid')


class PriceSerializer(serializers.ModelSerializer):

    ticker = TickerSerializer()

    class Meta:
        model = Price
        fields = ('created_on', 'unix_time', 'ticker')
