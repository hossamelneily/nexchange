from __future__ import absolute_import
from nexchange.tasks.base import BaseTask
import logging
from django.db.models import Q
from payments.models import Payment, PaymentPreference, PaymentMethod
from orders.models import Order
from core.models import Currency
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from copy import deepcopy
from orders.tasks.generic.base import BaseBuyOrderRelease
from decimal import Decimal


class BasePaymentChecker(BaseTask):
    def __init__(self, *args, **kwargs):
        self.currency_cache = {}
        self.transactions = []
        self.data = {}
        self.api = None
        self.payment_preference = None

        if self.name:
            self.last_payment = Payment.objects.filter(
                payment_preference__payment_method__name__icontains=self.name
            ).last()
        else:
            self.last_payment = Payment.objects.last()
        self.start_time = self.last_payment.api_time\
            if self.last_payment else None

        # TODO: consider using ABC
        self.abstract_methods = [
            'transactions_iterator',
            'get_transactions',
            'validate_beneficiary',
            'validate_success'
        ]

        self.required_data_keys = [
            'currency',
            'amount_cash',
            'unique_ref',
            'payment_system_id'
        ]

        self.essential_data_keys = [
            'beneficiary',
            'is_success'
        ]

        self.transaction_data_keys = [
            'identifier',
            'secondary_identifier',
            'currency',
            'amount_cash',
            'unique_ref',
            'payment_system_id'
        ]

        self.transaction_optional_keys = [
            'comment',
            'is_verified'
        ]

        self.payment_method = PaymentMethod.objects.get(
            name__icontains=self.name
        )
        self.payment_preference = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method=self.payment_method
        ).first()

        self.allowed_beneficiary = set(self.payment_preference.identifier)
        if self.payment_preference.secondary_identifier:
            self.allowed_beneficiary.add(
                self.payment_preference
                    .secondary_identifier
            )

        super(BasePaymentChecker, self).__init__(*args, **kwargs)

    def transactions_iterator(self):
        raise NotImplementedError

    def get_transactions(self):
        return self.api.get_transaction_history(self.start_time)

    def validate_beneficiary(self):
        try:
            to = self.data['beneficiary']
            assert to
        except (KeyError, AssertionError) as e:
            self.logger.error('no receiver wallet was given data: {} {}'
                              .format(__name__, self.data), e)
            return False
        except TypeError:
            self.logger.error('{} {} no data was given'
                              .format(__name__, self.data))
            return False

        return to in self.allowed_beneficiary

    def validate_success(self):
        try:
            success = self.data['is_success']
            assert success
            return success
        except AssertionError:
            self.logger.info('tried importing a provisional transaction, '
                             'pass data {}'.format(self.data))
            return False
        except KeyError:
            self.logger.error('{} no success status was given data: {}'
                              .format(__name__, self.data))
            return False
        except TypeError:
            self.logger.error('{} {} no data was given'
                              .format(__name__, self.data))
            return False

    def parse_data(self, trans):
        missing_required_keys =\
            [req_key for req_key in self.required_data_keys
                if req_key not in self.data]
        missing_essential_keys =\
            [req_key for req_key in self.essential_data_keys
                if req_key not in self.data]

        missing_required_values =\
            [(req_key, self.data[req_key],)
             for req_key in self.required_data_keys
                if req_key not in
             missing_required_keys and not self.data[req_key]]
        missing_essential_values =\
            [(req_key, self.data[req_key],)
             for req_key in self.essential_data_keys
                if req_key not in
             missing_essential_keys and not self.data[req_key]]

        missing_optional_keys = \
            [req_key for req_key in self.transaction_optional_keys
             if req_key not in self.data]
        missing_optional_values = \
            [(req_key, self.data[req_key],) for
             req_key in self.transaction_optional_keys
             if req_key not in
             missing_optional_keys and not self.data[req_key]]

        if missing_required_keys or missing_essential_keys:
            debug_msg = 'Payment serialization: {} missing keys essential:' \
                        ' {} missing keys required {} '\
                .format(self.data, missing_required_keys,
                        missing_essential_keys)
            turn_on_debug = 'for more info turn on debug'
            logging.error(debug_msg)
            e_message = 'ProgrammingError: Invalid serialisation!, ' \
                        'required or essential keys are missing.' \
                        'CHECK YOUR `parse_data` method {}' \
                .format(debug_msg if settings.DEBUG else turn_on_debug)
            raise ValueError(e_message)

        if any([missing_required_keys,
                missing_essential_keys,
                missing_essential_values,
                missing_essential_values]):
            logging.error('Payment serialization: {} missing keys: '
                          'required: {} essential: {}.'
                          ' missing values: required: {} essential: {}'
                          .format(self.data,
                                  missing_required_keys,
                                  missing_essential_keys,
                                  missing_required_values,
                                  missing_essential_values))

        if missing_optional_keys or missing_optional_values:
            self.logger.info('missing optional keys: {} values: {}'
                             .format(missing_optional_keys,
                                     missing_optional_values))

    def validate_transaction(self):
        success = self.validate_success()
        valid_beneficiary = self.validate_beneficiary()
        if not success:
            self.logger.error('Payment {} is not success'.format(self.data))
        if not valid_beneficiary:
            self.logger.error('Payment {} is not to our wallet Allowed: {}'
                              .format(self.data, self.allowed_beneficiary))

        return success and valid_beneficiary

    def check_order_paid_status(self, order):
        ref = order.unique_reference
        payments = Payment.objects.filter(is_success=True, reference=ref)
        sum_all = Decimal('0.0')
        for p in payments:
            sum_all += p.amount_cash
        amount_expected = order.amount_quote
        # FIXME: add transaction fee to customer on Payeer (or become a
        # partner)
        if order.payment_preference.payment_method.name == 'Payeer Wallet':
            # transaction fee 0.0095 , minimal fee 0.01 cent
            amount_expected = (amount_expected * Decimal('0.9905')) - Decimal(
                '0.01')
        if sum_all >= amount_expected:
            if order.status not in Order.IN_PAID:
                order.status = Order.PAID
                order.save()
        elif payments:
            order.status = Order.PAID_UNCONFIRMED
            order.save()

    def create_payment(self, pref, order=None):
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
                is_success=self.data['is_success'],
                payment_system_id=self.data['payment_system_id'],
                reference=self.data['unique_ref'],
                amount_cash=self.data['amount_cash'],
                payment_preference=pref,
                user=order.user if order else None,
                currency=self.get_currency()
            )
            payment.save()
            self.logger.info('new payment created {}'
                             .format(payment.__dict__))

            return payment
        return None

    def create_payment_preference(self, order=None):
        pref1, pref2 = (None, None,)
        # If we have no identifier ValueError is
        # thrown already at @see parse_data
        filters = {
            'payment_method': self.payment_method,
            'user': order.user if order else None
        }
        if self.data['identifier']:
            pref1_filters = deepcopy(filters)
            pref1_filters.update({'identifier': self.data['identifier']})
            pref1 = PaymentPreference.objects.filter(
                **pref1_filters
            )
        if self.data['secondary_identifier']:
            pref2_filters = deepcopy(filters)
            pref1_filters.update(
                {'secondary_identifier': self.data['secondary_identifier']}
            )

            pref2 = PaymentPreference.objects.filter(
                **pref2_filters
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
                payment_method=self.payment_method,
                user=order.user if order else None
            )
            if not order:
                flag, created = pref.flag()
                if created:
                    self.logger.warn('perf: {} without owner and order'
                                     .format(pref))

            self.logger.info(
                'payment preference created {} {}'.format(
                    pref, self.data))
        else:
            pref = pref1[0] if pref1 else pref2[0]

        pref.save()

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
                self.logger.error('payment {} currency DoesNotExist'
                                  .format(self.data))
        return db_curr

    def run(self):
        self.transactions = self.get_transactions()

        for trans in self.transactions_iterator():
            try:
                self.parse_data(trans)
            except ValueError as e:
                self.logger.warn(e)
                continue

            except KeyError as e:
                self.logger.warn(e)
                continue

            if not self.validate_transaction():
                continue
            order = Order.objects.filter(
                unique_reference=self.data['unique_ref']
            ).last()
            pref = self.create_payment_preference(order)
            payment = self.create_payment(pref, order)
            if order:
                self.check_order_paid_status(order)

            # only if new payment is created
            if payment:
                if payment.reference:
                    task = BaseBuyOrderRelease.RELEASE_BY_REFERENCE
                else:
                    task = BaseBuyOrderRelease.RELEASE_BY_RULE

                self.add_next_task(
                    task,
                    [payment.pk],
                    {
                        'countdown': 0 if order.withdraw_address else
                        settings.USER_SETS_WITHDRAW_ADDRESS_MEDIAN_TIME
                    }
                )

            super(BasePaymentChecker, self).run()
