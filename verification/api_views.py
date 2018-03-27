from .serializers import CreateVerificationSerializer, VerificationSerializer
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from collections import OrderedDict
from verification.models import Verification
from payments.models import Payment
from orders.models import Order


class VerificationViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          viewsets.GenericViewSet, mixins.ListModelMixin, ):

    model_class = Verification
    lookup_field = 'unique_reference'
    http_method_names = ['get', 'post']

    def retrieve(self, request, *args, **kwargs):
        is_verified = False
        id_document_status = None
        residence_document_status = None
        comment = 123
        try:
            order = Order.objects.get(**kwargs)
            assert(self.request.user == order.user)

            payment = order.payment_set.get(type=Payment.DEPOSIT)
            payment_preference = payment.payment_preference
            comment = getattr(order.user.verification_set.last(),
                              'user_visible_comment')\
                if self.request.user == order.user else None
            if payment_preference:
                is_verified = payment_preference.is_verified
                id_document_status = payment_preference.id_document_status
                residence_document_status = \
                    payment_preference.residence_document_status
        except Payment.DoesNotExist:
            pass
        except Order.DoesNotExist:
            pass
        data = {
            'is_verified': is_verified,
            'id_document_status': id_document_status,
            'residence_document_status': residence_document_status,
            'user_visible_comment': comment,
        }

        data = OrderedDict(data)
        return Response(data)

    def list(self, request):
        data = OrderedDict({'message': 'Cannot list KYC\'s'})
        return Response(data)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateVerificationSerializer
        if self.request.method == 'GET':
            return VerificationSerializer

        return super(VerificationViewSet, self).get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        return super(VerificationViewSet, self).perform_create(serializer)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # serializer
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = {'status': 'OK', 'message': 'KYC sent'}
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)
