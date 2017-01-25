from __future__ import absolute_import
from nexchange.tasks.base import BaseTask
import logging
from django.db.models import Q
from payments.models import Payment, PaymentPreference, PaymentMethod
from core.models import Currency
from django.core.exceptions import MultipleObjectsReturned


class BasePaymentChecker(BaseTask):

    def __init__(self, *args, **kwargs):
        self.currency_cache = {}
        self.transactions = []
        self.data = {}
        self.api = None
        self.payment_preference = None

        self.required_data_keys = [
            'currency',
            'amount_cash',
            'unique_ref',
            'payment_system_id'
        ]

        self.payment_method = PaymentMethod.objects.get(
            name__icontains=self.name
        )
        self.payment_preference = PaymentPreference.objects.get(
            user__is_staff=True,
            payment_method=self.payment_method
        )
        super(BasePaymentChecker, self).__init__(*args, **kwargs)

    def transactions_iterator(self):
        raise NotImplementedError

    def get_transactions(self):
        raise NotImplementedError

    def parse_data(self, trans):
        missing_keys =\
            [req_key for req_key in self.required_data_keys
                if req_key not in self.data]
        if missing_keys:
            logging.error("Payment serilization: {} missing keys: {}"
                          .format(self.data, missing_keys))
            raise ValueError("Invalid serialisation!")

    def validate_transaction(self, trans):
        success = self.validate_success(trans)
        valid_beneficiary = self.validate_beneficiary(trans)
        if not success:
            self.error("Payment {} is not success".format({}))
        if not valid_beneficiary:
            self.erro("Payment {} is not to our wallet".format({}))

        return success and valid_beneficiary

    def create_payment(self, pref):
        # get only by unique refs, even if the rest does not match
        # at the moment if the user pays the same invoice twice
        # we will not know about it and he will need to contact support
        existing_payment = None
        try:
            existing_payment = Payment.objects.get(
                payment_system_id=self.data['payment_system_id'],
            )
        except MultipleObjectsReturned:
            self.logger.error('more than one same payment exists in DB {}'
                              .format(self.data))
        except Payment.DoesNotExist:
            self.logger.info('{} payment not found in DB, creating new'
                             .format(self.data))

        if not existing_payment:
            payment = Payment.objects.create(
                payment_system_id=self.data['payment_system_id'],
                reference=self.data['unique_ref'],
                amount_cash=self.data['amount_cash'],
                payment_preference=pref,
                user=pref.user,
                currency=self.get_currency()
            )
            payment.save()
            self.logger.info('new payment created {}'
                             .format(payment.__dict__))

    def create_payment_preference(self):
        pref1, pref2 = (None, None,)
        # If we have no identifier ValueError is
        # thrown already at @see parse_data
        if self.data['identifier']:
            pref1 = PaymentPreference.objects.filter(
                identifier=self.data['identifier'],
                payment_method=self.payment_method
            )
        if self.data['secondary_identifier']:
            pref2 = PaymentPreference.objects.filter(
                secondary_identifier=self.data['secondary_identifier'],
                payment_method=self.payment_method
            )
        new_pref = not pref1 and not pref2
        if pref1 and pref2 and pref1[0] != pref2[0]:
            self.logger.error('found duplicate payment preferences {} {}'
                              .format(pref1, pref2))
        if new_pref:
            # creating a pref without a user, after payment
            # will be matched with an order we will assign it
            # to the user who made the order
            pref = PaymentPreference.objects.create(
                identifier=self.data['identifier'],
                secondary_identifier=self.data['secondary_identifier'],
                payment_method=self.payment_method
            )
            pref.save()
        else:
            pref = pref1[0] if pref1 else pref2[0]

            self.logger.info(
                'payment preference created {} {}'.format(
                    pref, self.data))

        return pref

    def get_currency(self):
        db_curr = self.currency_cache.get(self.data['currency'])
        if not db_curr:
            try:
                db_curr = Currency.objects.get(
                    Q(name=self.data['currency']) |
                    Q(code=self.data['currency'].upper())
                )
                self.currency_cache[self.data['currency']] = db_curr
            except Currency.DoesNotExist:
                db_curr = None
                self.logger.error("payment {} currency DoesNotExist"
                                  .format(self.data))
        return db_curr

    def validate_beneficiary(self, trans):
        raise NotImplementedError

    def validate_success(self, trans):
        raise NotImplementedError

    def run(self):
        self.get_transactions()

        for trans in self.transactions_iterator():
            if not self.validate_success(trans):
                continue

            try:
                self.parse_data(trans)
            except ValueError:
                continue

            pref = self.create_payment_preference()
            self.create_payment(pref)
