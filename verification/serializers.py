from rest_framework import serializers
from rest_framework.fields import CharField, FileField
from .models import Verification, VerificationDocument, DocumentType
from payments.models import Payment
from orders.models import Order
from core.common.fields import PrivateField
from .validators import validate_image_extension


class MetaVerification:
    model = Verification
    fields = ('order_reference', 'full_name', 'user_input_comment')


class CreateVerificationSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super(CreateVerificationSerializer, self).__init__(*args, **kwargs)
        doc_types = DocumentType.objects.all()
        for doc_type in doc_types:
            self.fields[doc_type.api_key] = FileField(
                allow_null=True, max_length=100, required=False,
                validators=[validate_image_extension]
            )
        self.documents_data = {
            doc_type.api_key: None for doc_type in doc_types
        }

    order_reference = CharField()

    class Meta(MetaVerification):
        pass

    def create(self, data):
        order = None
        order_reference = data.pop('order_reference', None)
        for api_key in self.documents_data.keys():
            self.documents_data[api_key] = data.pop(api_key, None)
        order_args = {'unique_reference': order_reference}
        verification = Verification(**data)
        verification.note = order_reference
        order_list = Order.objects.filter(**order_args)
        data['note'] = order_reference
        verification = Verification(**data)
        if order_list.count() == 1:
            _verifications = Verification.objects.filter(**data)
            if _verifications:
                verification = _verifications.latest('id')
        if order_list:
            order = order_list.latest('id')
            payments = order.payment_set.filter(type=Payment.DEPOSIT)
            if payments:
                payment = payments.latest('id')
                pref = payment.payment_preference
                verification.payment_preference = pref

        verification.save()
        for key, value in self.documents_data.items():
            if not value:
                continue
            doc_type = DocumentType.objects.get(api_key=key)
            doc = VerificationDocument(
                verification=verification,
                document_file=value,
                document_type=doc_type
            )
            if doc_type.whitelisted_address_required and order:
                doc.whitelisted_address = order.withdraw_address
            doc.save()

        # get post_save stuff in sync
        verification.refresh_from_db()
        return verification


class VerificationSerializer:
    class Meta(MetaVerification):
        fields = MetaVerification.fields + ('user_visible_comment',)

    user_visible_comment = PrivateField()
