from core.tests.base import OrderBaseTestCase
from payments.models import Payment, PaymentPreference
from orders.task_summary import buy_order_release_by_wallet_invoke as \
    wallet_release, \
    buy_order_release_by_reference_invoke as ref_release, \
    buy_order_release_by_rule_invoke as rule_release
from orders.models import Order
from core.models import Address, Currency
from decimal import Decimal
from unittest.mock import patch, MagicMock
from copy import deepcopy
from django.db import transaction
from core.tests.utils import data_provider
from django.contrib.auth.models import User
import random


class BaseOrderReleaseTestCase(OrderBaseTestCase):

    def generate_orm_obj(self, _constructor, base_data, modifiers=None):
        objs = []
        for modifier in modifiers:
            actual_data = deepcopy(base_data)
            actual_data.update(modifier)
            _obj = _constructor(**actual_data)
            _obj.save()
            _obj.refresh_from_db()
            objs.append(_obj)
        return objs

    def purge_orm_objects(self, *args):
        for objs in args:
            while len(objs):
                obj = objs.pop()
                obj.delete()

    def setUp(self):
        super(BaseOrderReleaseTestCase, self).setUp()
        currency = self.RUB
        self.payments = []
        self.orders = []
        self.addr = Address(address='12345', user=self.user)
        self.addr.save()
        self.our_pref = PaymentPreference.objects.first()
        self.order_data = {
            'amount_cash': '30674.85',
            'amount_btc': Decimal(1.00),
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '123456',
            'payment_preference': self.our_pref,
            'currency': currency,
            'withdraw_address': self.addr,
        }

        self.pref, created = PaymentPreference.objects.get_or_create(
            payment_method=self.our_pref.payment_method,
            user=self.user,
            identifier='1234567',
        )

        self.pref.currency.add(currency)
        self.pref.save()

        self.base_payment_data = {
            'user': self.user,
            'currency': currency,
            'payment_preference': self.pref,
            'amount_cash': 30674.85,
            'is_success': True
        }

    def tearDown(self):
        with transaction.atomic(using='default'):
            self.purge_orm_objects(self.orders,
                                   self.payments)


# TODO: Those tests can be heavily optimised in length by data providers
class BuyOrderReleaseByReferenceTestCase(BaseOrderReleaseTestCase):

    @data_provider(
        lambda: (
            # Test single release by reference (pass multiple function if
            # rest of the params are the same)
            # fail release by ref/wallet - payment not success
            ([ref_release, wallet_release],
             [{'is_default_rule': False,
               'unique_reference': 'correct_ref1'}],
             [{'reference': 'correct_ref1', 'is_success': False}],
             [{'is_released': False}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'blabla1'}],
             [{'reference': 'blabla1', 'is_success': True}],
             [{'is_released': True}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # Triple release by reference (do not release more than once!)
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'blabla2'}],
             [{'reference': 'blabla2'}],
             [{'is_released': True}],
             [{'is_complete': True}],
             3,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref - incorrect ref
            ([ref_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref'}],
             [{'reference': 'incorrect_ref'}],
             [{'is_released': False}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref/wallet - incorrect payment amount
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref1'}],
             [{'reference': 'correct_ref1', 'amount_cash': 123}],
             [{'is_released': False}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref - incorrect payment currency
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref2'}],
             [{'reference': 'correct_ref2',
               'currency': Currency.objects.get(
                   code='USD')}
              ],
             [{'is_released': False}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref - incorrect payment user
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref3'}],
             [{'reference': 'correct_ref3',
               'user': User.objects.create(username='zaza')}
              ],
             [{'is_released': False}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by wallet - correct ref
            ([wallet_release],
             [{'is_default_rule': False, 'unique_reference':
                 'correct_ref4'}],
             [{'reference': 'correct_ref4'}],
             [{'is_released': True}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by wallet - no ref
            ([wallet_release],
             [{'is_default_rule': False, 'unique_reference':
                 'correct_ref5'}],
             [{'reference': ''}],
             [{'is_released': True}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by even with wrong info (by wallet)
            ([wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref6'}],
             [{'reference': 'incorrect_ref'}],
             [{'is_released': True}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by even with wrong preceding payments
            # mutual cases for release by wallet and by reference
            ([ref_release, wallet_release],
             [
                 {'is_default_rule': False, 'unique_reference':
                     'correct_ref7'},
            ],
                [
                 {'user': User.objects.create(username='zaza2')},
                 {'currency': Currency.objects.get(code='USD')},
                 {'amount_cash': 321},
                 {'is_success': False},
                 {'reference': 'correct_ref7'}  # correct one!
            ],
                [{'is_released': True}],
                [
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': True},
            ],
                1,  # call count
                1,  # actual invoke time
                1,  # order count after exec
            ),

            # success release by even with wrong preceding payments
            # cases only for ref relese
            ([ref_release],
             [
                 {'is_default_rule': False, 'unique_reference':
                     'correct_ref8'},
            ],
                [
                 {'reference': 'incorrect_ref8'},  # incorrect one!
                 {'user': User.objects.create(username='zaza3')},
                 {'currency': Currency.objects.get(code='USD')},
                 {'amount_cash': 321},
                 {'is_success': False},
                 {'reference': 'correct_ref8'}  # correct one!
            ],
                [{'is_released': True}],
                [
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': True},
            ],
                1,  # call count
                1,  # actual invoke time
                1,  # order count after exec
            ),

            # success release by even with wrong preceding payments
            # cases only for ref release
            ([wallet_release],
             [
                 {'is_default_rule': False, 'unique_reference':
                     'correct_ref9'},
                 {'is_default_rule': False, 'unique_reference':
                     'correct_ref10', 'amount_cash': 4.20},
            ],
                [
                 {'reference': 'SomeRandomRef'},  # released by wallet
                 {'user': User.objects.create(username='zaza4')},
                 {'currency': Currency.objects.get(code='USD')},
                 {'amount_cash': 321},
                 {'is_success': False},
                 {'amount_cash': 4.20},
                 {'reference': ''}  # no reference
            ],
                [{'is_released': True},
                 {'is_released': True}
                 ],
                [
                 {'is_complete': True},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': False},
                 {'is_complete': True},
                 {'is_complete': False},  # Payment with no order! shit!
            ],
                2,  # call count
                2,  # actual invoke time
                2,  # order count after exec
            ),

            # REGRESSION!
            # release after having a payment with no sender
            ([wallet_release, ref_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref11'}],
             [{'user': None}, {'reference': 'correct_ref11'}],
             [
                 {'is_released': True}
            ],
                [
                 {'is_complete': False},
                 {'is_complete': True},
            ],
                1,  # call count
                1,  # actual invoke time
                1,  # order count after exec
            ),

        )
    )
    @patch('orders.models.Order.convert_coin_to_cash')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    def test_releases(self,
                      # data_provider args
                      tested_fns, order_modifiers,
                      payment_modifiers,
                      order_expects,
                      payment_expects,
                      release_count,
                      invoke_count,
                      order_count,
                      # stabs!
                      send_email, send_sms,
                      convert_coin_to_cash):

        for tested_fn in tested_fns:
            with patch('orders.tasks.generic.base.release_payment') as \
                    release_payment:

                self.purge_orm_objects(self.orders,
                                       self.payments)

                self.payments += self.generate_orm_obj(
                    Payment,
                    self.base_payment_data,
                    payment_modifiers
                )
                self.orders += self.generate_orm_obj(
                    Order,
                    self.order_data,
                    order_modifiers
                )

                for _payment in self.payments:
                    release_payment.return_value = \
                        ('%06x' % random.randrange(16 ** 16)).upper()
                    for i in range(release_count):
                        myargs = [_payment.pk]
                        res = tested_fn.apply(myargs)  # noqa
                        # self.assertEqual('SUCCESS', res.state)

                # reload from db
                for order in self.orders:
                    order.refresh_from_db()
                for _payment in self.payments:
                    _payment.refresh_from_db()
                # test only once!
                self.assertEqual(invoke_count, release_payment.call_count)
                self.assertEqual(order_count, Order.objects.all().count())

                test_subjects = [self.payments, self.orders]
                expects_list = [payment_expects, order_expects]
                for outer_count, expects in enumerate(expects_list):
                    for count, prop_list in enumerate(expects):
                        subject = test_subjects[outer_count][count]
                        for prop, expected in prop_list.items():
                            try:
                                actual = getattr(subject, prop)
                                self.assertEqual(expected,
                                                 actual)
                            except AssertionError as e:
                                print(subject, prop)
                                raise e

    @data_provider(
        lambda: (
            (True,
             {'notify_by_phone': True,
              'notify_by_email': True, 'lang': 'en'}, 1, 1),
            (True,
             {'notify_by_phone': False, 'notify_by_email': True,
              'lang': 'en'}, 0, 1),
            (True,
             {'notify_by_phone': True, 'notify_by_email': False,
              'lang': 'en'}, 1, 0),
            (True,
             {'notify_by_phone': False, 'notify_by_email': False,
              'lang': 'en'},
             0, 0),
            (False,
             {'notify_by_phone': False, 'notify_by_email': False,
              'lang': 'en'},
             0, 0),
            (False,
             {'notify_by_phone': True, 'notify_by_email': True,
              'lang': 'en'},
             0, 0)
        )
    )
    @patch('orders.task_summary.release_by_ref.do_release')
    @patch('orders.task_summary.release_by_wallet.do_release')
    @patch('orders.task_summary.release_by_rule.do_release')
    @patch('orders.task_summary.release_by_ref.get_order')
    @patch('orders.task_summary.release_by_wallet.get_order')
    @patch('orders.task_summary.release_by_rule.get_order')
    @patch('orders.task_summary.release_by_ref.validate')
    @patch('orders.task_summary.release_by_wallet.validate')
    @patch('orders.task_summary.release_by_rule.validate')
    @patch('orders.task_summary.release_by_ref.get_profile')
    @patch('orders.task_summary.release_by_wallet.get_profile')
    @patch('orders.task_summary.release_by_rule.get_profile')
    @patch('orders.tasks.generic.base.send_sms')
    @patch('orders.tasks.generic.base.send_email')
    @patch('orders.tasks.generic.base.Payment.objects.get')
    def test_notification(self,
                          # data provider
                          release_return_val,
                          profile_props, expect_notify_by_phone,
                          expect_notify_by_email,
                          # notification
                          payment_getter,
                          send_email, send_sms,
                          # get profile mocks
                          get_profile_wallet, get_profile_ref,
                          get_profile_rule,
                          # release stabs
                          release_by_rule,
                          release_by_wallet, release_by_ref,
                          # validation stabs
                          validate_order_rule, validate_order_wallet,
                          validate_order_ref,
                          get_order_wallet, get_order_ref,
                          get_order_rule):

        release_mocks = [release_by_rule, release_by_ref, release_by_wallet]
        release_fns = [wallet_release, ref_release, rule_release]
        get_order_mocks = [get_order_wallet, get_order_ref, get_order_rule]
        get_profile_mocks = [get_profile_wallet, get_profile_ref,
                             get_profile_rule]
        validate_mocks = [validate_order_wallet, validate_order_rule,
                          validate_order_ref]
        payment_getter.return_value = MagicMock()
        for fn in release_fns:
            send_sms.call_count, send_email.call_count = 0, 0
            payment_id = 1
            order = Order(**self.order_data)
            self.orders.append(order)
            profile = order.user.profile

            # preps
            for release_mock in release_mocks:
                release_mock.return_value = release_return_val

            for get_order_mock in validate_mocks:
                get_order_mock.return_value = MagicMock()

            for get_order_mock in get_order_mocks:
                _order = MagicMock()
                get_order_mock.return_value = _order

            for get_profile in get_profile_mocks:
                get_profile.return_value = profile

            for prop, value in profile_props.items():
                setattr(profile, prop, value)
                profile.save()

            res = fn.apply([payment_id])
            self.assertEqual('SUCCESS', res.state)
            self.assertEqual(expect_notify_by_email, send_email.call_count)
            self.assertEqual(expect_notify_by_phone, send_sms.call_count)

    # TODO: move to utils tests (validate_payment)
    # TODO: Tests for rule-order using the data provider
    # Todo Tests for sell release order
    def test_release_fail_payment_other_user(self):
        pass

    def test_release_fail_other_currency(self):
        pass
