from rest_framework import serializers
from risk_management.models import PNLSheet, PNL
from core.serializers import SimplePairSerializer
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as RestValidationError


class PNLSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PNLSheet
        fields = ('date_from', 'date_to', 'period', 'pnl_btc', 'pnl_usd',
                  'positions', 'btc_pnls')

    def create(self, validated_data):
        pnl_sheet = PNLSheet(**validated_data)
        try:
            pnl_sheet.save()
            pnl_sheet.refresh_from_db()
            return pnl_sheet
        except ValidationError as e:
            raise RestValidationError({'non_field_errors': [e.message]})


class PNLSerializer(serializers.ModelSerializer):
    pair = SimplePairSerializer(many=False, read_only=False)

    class Meta:
        model = PNL
        fields = (
            'date_from', 'date_to', 'period', 'pair', 'average_ask',
            'average_bid', 'volume_ask', 'volume_bid',
            'base_volume_ask', 'base_volume_bid', 'exit_price', 'rate_btc',
            'rate_usd', 'rate_eur', 'rate_eth'
        )
