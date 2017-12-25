from rest_framework import serializers
from rest_framework.fields import CharField
from .models import Verification
from payments.models import Payment
from orders.models import Order


class CreateKycSerializer(serializers.ModelSerializer):

    order_reference = CharField()

    class Meta:
        model = Verification
        fields = ('identity_document', 'utility_document', 'order_reference',
                  'full_name')

    def create(self, data):
        order_reference = data.pop('order_reference')
        order_args = {'unique_reference': order_reference}
        verification = Verification(**data)
        verification.note = order_reference
        order_list = Order.objects.filter(**order_args)
        if order_list:
            order = order_list[0]
            payments = order.payment_set.filter(type=Payment.DEPOSIT)
            if payments:
                payment = payments[0]
                pref = payment.payment_preference
                verification.payment_preference = pref

        verification.save()
        # get post_save stuff in sync
        verification.refresh_from_db()
        return verification
