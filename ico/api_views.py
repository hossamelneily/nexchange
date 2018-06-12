from rest_framework import viewsets
from .serializers import SubscriptionSerializer
from .models import Subscription
from nexchange.permissions import PostOnlyPermission
from nexchange.utils import get_nexchange_logger
from django.contrib.auth.models import User
from orders.models import Order
from django.db import Error


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

            orders = Order.objects.filter(
                withdraw_address__address=instance.sending_address
            )

            for order in orders:
                instance.orders.add(order)
                instance.users.add(order.user)
        except Error as e:
            logger = get_nexchange_logger(__name__)
            logger.error('Email Subscription User lookup error {} {}'
                         .format(instance.email, e))

        super(SubscriptionViewSet, self).perform_create(serializer)
