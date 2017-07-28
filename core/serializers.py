from rest_framework import serializers
from core.models import Pair


class PairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pair
        fields = ('base', 'qoute')


class NestedPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pair
        fields = ('base', 'qoute')