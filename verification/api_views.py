from .serializers import CreateVerificationSerializer, VerificationSerializer
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from collections import OrderedDict
from verification.models import Verification, DocumentType
from payments.models import Payment
from orders.models import Order


class VerificationViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          viewsets.GenericViewSet, mixins.ListModelMixin, ):

    model_class = Verification
    lookup_field = 'unique_reference'
    http_method_names = ['get', 'post']

    def retrieve(self, request, *args, **kwargs):
        is_verified = False
        residence_document_status = None
        comment = None
        out_of_limit = None
        limits = None
        data = {}
        try:
            order = Order.objects.get(**kwargs)

            payment = order.payment_set.get(type=Payment.DEPOSIT)
            payment_preference = payment.payment_preference
            if payment_preference:
                _show_private_data = \
                    self.request.user == order.user or \
                    self.request.user.is_staff
                is_verified = payment_preference.is_verified
                residence_document_status = Verification.STATUSES_TO_API[
                    payment_preference.residence_document_status
                ]
                for doc_type in DocumentType.objects.all():
                    key = '{}_document_status'.format(doc_type.name.lower())
                    _status = payment_preference.get_payment_preference_document_status(doc_type.name)  # noqa
                    data[key] = Verification.STATUSES_TO_API[_status]
                out_of_limit = payment_preference.out_of_limit
                limits = payment_preference.trade_limits_info \
                    if _show_private_data else None
                last_verification = payment_preference.verification_set.last()
                if last_verification:
                    comment = last_verification.user_visible_comment \
                        if _show_private_data else None
        except Payment.DoesNotExist:
            pass
        except Order.DoesNotExist:
            pass
        except AssertionError:
            pass
        data.update({
            'is_verified': is_verified,
            'residence_document_status': residence_document_status,
            'user_visible_comment': comment,
            'out_of_limit': out_of_limit,
            'limits_message': limits,
        })

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
        if self.request.user.is_authenticated:
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
