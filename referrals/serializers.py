from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from referrals.models import Program, Referral, ReferralCode


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ('name', 'percent_first_degree',
                  'max_users', 'max_payout_btc')


class ReferralCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCode
        fields = ('code', 'created_on', 'modified_on')


class RefereeProfileSerializer(serializers.ModelSerializer):
    partial_phone = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = ('partial_phone', 'last_visit_time', 'id', 'time_zone',
                  'created_on', 'modified_on')
        depth = 3


class RefereeSerializer(serializers.ModelSerializer):
    profile = RefereeProfileSerializer()

    class Meta:
        model = User
        fields = ('profile',)


class ReferralSerializer(serializers.ModelSerializer):
    confirmed_orders_count = serializers.ReadOnlyField()
    turnover = serializers.ReadOnlyField()
    revenue = serializers.ReadOnlyField()
    referee = RefereeSerializer()
    code = ReferralCodeSerializer()

    class Meta:
        model = Referral
        fields = ('confirmed_orders_count', 'turnover', 'revenue', 'referee', 'code',
                  'created_on', 'modified_on')
        depth = 3
