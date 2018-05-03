from rest_framework import viewsets
from .serializers import SubscriptionSerializer
from .models import Subscription
from nexchange.permissions import PostOnlyPermission


class SubscriptionViewSet(viewsets.ModelViewSet):
    model_class = Subscription
    serializer_class = SubscriptionSerializer
    permission_classes = (PostOnlyPermission,)
    http_method_names = ['post']
