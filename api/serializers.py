from rest_framework import serializers
from referrals.models import Referral, Program
from core.models import Profile


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ('name', 'percent_first_degree',
                  'max_users', 'max_payout_btc')


class RefereeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('partial_phone', 'last_seen')


class ReferralSerializer(serializers.ModelSerializer):
    referee = RefereeSerializer
    program = ProgramSerializer

    class Meta:
        model = Referral
        fields = ('confirmed_orders_count', 'turnover', 'revenue')
