from rest_framework import serializers

from ticker.models import Price, Ticker
from core.models import Market


class MarketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ('name', 'code')


class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = ('ask', 'bid')


class PriceSerializer(serializers.ModelSerializer):

    ticker = TickerSerializer()
    market = MarketSerializer()

    class Meta:
        model = Price
        fields = ('created_on', 'unix_time', 'ticker', 'market')
