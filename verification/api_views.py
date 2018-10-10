from .serializers import CreateVerificationSerializer, VerificationSerializer
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from collections import OrderedDict
from verification.models import Verification, DocumentType
from payments.models import Payment, PaymentPreference
from orders.models import Order
from .task_summary import send_verification_upload_email


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
        whitelisted_addresses = []
        data = {}
        order = None
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
                id_status = payment_preference.\
                    get_payment_preference_document_status('id')
                data['identity_token'] = \
                    order.identity_token if id_status in [
                        Verification.REJECTED,
                        None] else None
                whitelisted_addresses = \
                    payment_preference.whitelisted_addresses
                whitelisted = order.withdraw_address in whitelisted_addresses
                out_of_limit = \
                    payment_preference.out_of_limit and not whitelisted
                limits = payment_preference.trade_limits_info
                if limits:
                    limits.update({
                        'whitelisted_addresses': [
                            a.address for a in whitelisted_addresses
                        ],
                        'whitelisted_addresses_info': {
                            k.address: Verification.STATUSES_TO_API[v]
                            for k, v in payment_preference.
                            whitelisted_addresses_info.items()
                        }
                    })
                last_verification = payment_preference.verification_set.last()
                if last_verification:
                    comment = last_verification.user_visible_comment \
                        if _show_private_data else None
        except (Order.DoesNotExist, Payment.DoesNotExist):
            refs = [kwargs['unique_reference']]
            if order:
                refs = [o.unique_reference for o in Order.objects.filter(
                    user=order.user
                )]
            vers = Verification.objects.filter(note__in=refs)
            dummy_pref = PaymentPreference()
            _residence_status = dummy_pref._get_utility_document_status(
                verifications=vers
            )
            residence_document_status = Verification.STATUSES_TO_API[
                _residence_status
            ]
            for doc_type in DocumentType.objects.all():
                key = '{}_document_status'.format(doc_type.name.lower())
                _status = \
                    dummy_pref.get_payment_preference_document_status(
                        doc_type.name, verifications=vers
                    )
                data[key] = Verification.STATUSES_TO_API[_status]
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
        res = super(VerificationViewSet, self).perform_create(serializer)
        send_verification_upload_email.apply_async([serializer.instance.pk])
        return res

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # serializer
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = {'status': 'OK', 'message': 'KYC sent'}
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)
