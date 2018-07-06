from rest_framework import viewsets
from .serializers import SubscriptionSerializer
from .models import Subscription
from nexchange.permissions import PostOnlyPermission
from nexchange.utils import get_nexchange_logger
from django.contrib.auth.models import User
from django.db import Error
from django.conf import settings
from referrals.middleware import ReferralMiddleWare
from .task_summary import subscription_eth_balance_check_invoke,\
    subscription_address_turnover_check_invoke,\
    subscription_token_balances_check_invoke,\
    subscription_related_turnover_check_invoke


referral_middleware = ReferralMiddleWare()


class SubscriptionViewSet(viewsets.ModelViewSet):
    model_class = Subscription
    serializer_class = SubscriptionSerializer
    permission_classes = (PostOnlyPermission,)
    http_method_names = ['post']

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            if self.request.user.is_authenticated:
                instance.users.add(self.request.user)

            if instance.email:
                try:
                    user = User.objects.get(email=instance.email)
                    instance.users.add(user)
                except User.DoesNotExist:
                    pass

            instance.add_related_orders_and_users()
            instance.referral_code = \
                referral_middleware.get_referral_code(self.request)
            instance.save()
        except Error as e:
            logger = get_nexchange_logger(__name__)
            logger.error('Email Subscription User lookup error {} {}'
                         .format(instance.email, e))

        super(SubscriptionViewSet, self).perform_create(serializer)
        subscription_eth_balance_check_invoke.apply_async([instance.pk])
        subscription_address_turnover_check_invoke.apply_async(
            [instance.pk],
            countdown=settings.FAST_TASKS_TIME_LIMIT
        )
        subscription_related_turnover_check_invoke.apply_async(
            [instance.pk],
            countdown=settings.FAST_TASKS_TIME_LIMIT * 2
        )
        subscription_token_balances_check_invoke.apply_async(
            [instance.pk],
            countdown=settings.FAST_TASKS_TIME_LIMIT * 3
        )
