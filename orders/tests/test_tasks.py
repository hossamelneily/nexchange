from core.tests.base import OrderBaseTestCase
from payments.models import Payment, PaymentPreference
from orders.task_summary import buy_order_release_by_wallet_invoke as \
    wallet_release, \
    buy_order_release_by_reference_invoke as ref_release, \
    buy_order_release_reference_periodic as ref_periodic_release
from orders.models import Order
from core.models import Address, Currency, Pair
from core.common.models import Flag
from decimal import Decimal
from unittest.mock import patch, PropertyMock
from copy import deepcopy
from django.db import transaction
from core.tests.utils import data_provider, get_ok_pay_mock,\
    create_ok_payment_mock_for_order
from django.contrib.auth.models import User
import random
import requests_mock
from payments.task_summary import run_okpay


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

    def edit_orm_obj(self, object, modifiers):
        for modifier, value in modifiers.items():
            setattr(object, modifier, value)
            object.save()
            object.refresh_from_db()
        return object

    def setUp(self):
        super(BaseOrderReleaseTestCase, self).setUp()
        self.payments = []
        self.orders = []
        self.addr = Address(address='12345', user=self.user)
        self.addr.save()
        self.our_pref = PaymentPreference.objects.first()
        self.order_data = {
            'amount_quote': Decimal(30674.85),
            'amount_base': Decimal(1.00),
            'user': self.user,
            'admin_comment': 'tests Order',
            'unique_reference': '123456',
            'payment_preference': self.our_pref,
            'withdraw_address': self.addr,
            'pair': self.BTCRUB,
        }

        self.pref, created = PaymentPreference.objects.get_or_create(
            payment_method=self.our_pref.payment_method,
            user=self.user,
            identifier='1234567',
        )

        self.pref.currency.add(self.BTCRUB.quote)
        self.pref.save()

        self.base_payment_data = {
            'user': self.user,
            'currency': self.BTCRUB.quote,
            'payment_preference': self.pref,
            'amount_cash': self.order_data['amount_quote'],
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
             [{'status': Order.INITIAL}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # subjects
            ([ref_release, wallet_release],
             # modifiers
             [{'is_default_rule': False, 'unique_reference': 'blabla1'}],
             [{'reference': 'blabla1', 'is_success': True}],
             # expectations
             [{'status': Order.RELEASED}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # Triple release by reference (do not release more than once!)
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'blabla2'}],
             # modifier
             [{'reference': 'blabla2'}],
             # expects
             [{'status': Order.RELEASED}],
             [{'is_complete': True}],
             3,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref - incorrect ref
            ([ref_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref'}],
             [{'reference': 'incorrect_ref'}],
             [{'status': Order.INITIAL}],
             [{'is_complete': False}],
             1,  # call count
             0,  # actual invoke time
             1,  # order count after exec
             ),

            # fail release by ref/wallet - incorrect payment amount
            ([ref_release, wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref1'}],
             [{'reference': 'correct_ref1', 'amount_cash': 123}],
             [{'status': Order.INITIAL}],
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
             [{'status': Order.INITIAL}],
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
             [{'status': Order.INITIAL}],
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
             [{'status': Order.RELEASED}],
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
             [{'status': Order.RELEASED}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by even with wrong info (by wallet)
            ([wallet_release],
             [{'is_default_rule': False, 'unique_reference': 'correct_ref6'}],
             [{'reference': 'incorrect_ref'}],
             [{'status': Order.RELEASED}],
             [{'is_complete': True}],
             1,  # call count
             1,  # actual invoke time
             1,  # order count after exec
             ),

            # success release by even with wrong preceding payments
            # mutual cases for release by wallet and by reference
            ([ref_release, wallet_release],
             # modifiers
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
            ],  # expects
                [{'status': Order.RELEASED}],
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
            # cases only for ref release
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
                [{'status': Order.RELEASED}],
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
                     'correct_ref10', 'amount_quote': 4.20},
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
                [{'status': Order.RELEASED},
                 {'status': Order.RELEASED}
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
                 {'status': Order.RELEASED}
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
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
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
            with patch('nexchange.api_clients.uphold.UpholdApiClient.'
                       'release_coins') as release_payment:

                self.purge_orm_objects(self.payments, self.orders)
                # workaround to delete unpurgeble records
                Order.objects.all().delete()
                Payment.objects.all().delete()

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

                # TODO: will only work if order asigned to payment at import
                # TODO: I.E. BEFORE IMPORT
                self.payments[-1].order = self.orders[-1]
                self.payments[-1].save()
                for _payment in self.payments:
                    release_payment.return_value = \
                        ('%06x' % random.randrange(16 ** 16)).upper()
                    for i in range(release_count):
                        myargs = [_payment.pk]
                        res = tested_fn.apply(myargs)  # noqa

                    self.assertEqual(None, res.traceback)
                    self.assertEqual('SUCCESS', res.state)

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
            ({'username': 'u1'},
             {'notify_by_phone': True, 'notify_by_email': True,
              'phone': '+37068644145', 'lang': 'en'}, 1, 0),
            ({'username': 'u2'},
             {'notify_by_phone': True, 'notify_by_email': True,
              'phone': '+37068644146', 'lang': 'en'}, 1, 0),
            ({'username': 'u3', 'email': 'test@email.com'},
             {'notify_by_phone': True, 'notify_by_email': True,
              'phone': '+37068644147',
              'lang': 'en'}, 1, 1),
            ({'username': 'u4', 'email': 'test@email.com'},
             {'notify_by_phone': False, 'notify_by_email': True,
              'phone': '+37068644148',
              'lang': 'en'}, 0, 1),
            ({'username': 'u5', 'email': 'test@email.com'},
             {'notify_by_phone': True, 'notify_by_email': False,
              'phone': '+37068644149',
              'lang': 'en'}, 1, 0),
            ({'username': 'u6', 'email': 'test@email.com'},
             {'notify_by_phone': False, 'notify_by_email': False,
              'phone': '+37068644150',
              'lang': 'en'}, 0, 0),
            ({'username': 'u7', 'email': 'test@email.com'},
             {'notify_by_phone': False, 'notify_by_email': False,
              'phone': '+37068644151',
              'lang': 'en'}, 0, 0),
        )
    )
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_notification(self,
                          # data provider
                          user_props, profile_props, expect_notify_by_phone,
                          expect_notify_by_email,
                          # notification
                          send_email, send_sms):

        with requests_mock.mock() as m:
            self._mock_cards_reserve(m)
            user = User.objects.get_or_create(**user_props)[0]
        order = Order(**self.order_data)
        order.user = user
        order.save()
        profile = user.profile
        for prop, value in profile_props.items():
            setattr(profile, prop, value)
            profile.save()

        self.assertEqual(order.status, Order.INITIAL)
        statuses = [Order.PAID_UNCONFIRMED, Order.PAID, Order.RELEASED,
                    Order.COMPLETED]
        for i, status in enumerate(statuses):
            order.status = status
            order.save()
            # Second save with same status change
            order.save()

            self.assertEqual(
                expect_notify_by_email * (i + 1), send_email.call_count,
                'user:{}, profile:{}'.format(user_props, profile_props)
            )
            self.assertEqual(
                expect_notify_by_phone * (i + 1), send_sms.call_count,
                'user:{}, profile:{}'.format(user_props, profile_props)
            )

    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.send_sms')
    @patch('orders.models.send_email')
    def test_set_user_on_match(self, send_email, send_sms, release_payment):
        release_payment.return_value = 'A555B'
        self.payment = Payment(**self.base_payment_data)
        self.payment.save()

        self.order = Order(**self.order_data)
        self.order.save()

        wallet_release.apply()

        self.payment.refresh_from_db()

        # for easiness
        p = self.payment
        self.assertEqual(p.payment_preference.user,
                         self.order.user)
        self.assertEquals(p.user, self.order.user, p.payment_preference.user)

# TODO: move to utils tests (validate_payment)
# TODO: Tests for rule-order using the data provider
# Todo Tests for sell release order

# TODO: Those tests can be heavily optimised in length by data providers


class BuyOrderReleaseFailedFlags(BaseOrderReleaseTestCase):

    def setUp(self):
        super(BuyOrderReleaseFailedFlags, self).setUp()
        self.our_pref = PaymentPreference.objects.get(
            identifier='okpay@nexchange.co.uk'
        )
        self.order_data['payment_preference'] = self.our_pref
        self.release_task = ref_periodic_release

    @data_provider(
        lambda: (
            ('Flagged when order.is_paid==False due to amount_quote changes',
             [{'unique_reference': 'correct_ref123'}],
             {'amount_quote': 10000000},
             ['order_paid==False'],
             True,
             True,
             ),
            ('Flagged when order.is_paid==False due to pair changes',
             [{'unique_reference': 'correct_ref124'}],
             {'pair': Pair.objects.get(name='BTCUSD')},
             ['order_paid==False', 'details_match==False'],
             True,
             True,
             ),
            ('Flagged when order user changed',
             [{'unique_reference': 'correct_ref125'}],
             {'user': User.objects.get(username='onit')},
             ['order.user!=payment.user'],
             True,
             True,
             ),
            ('Flagged when user is not verified for buying',
             [{'unique_reference': 'correct_ref126'}],
             {},
             ['verification_passed==False'],
             True,
             False,
             ),
            ('Flagged when reference is wrong',
             [{'unique_reference': 'incorrect_ref127'}],
             {'unique_reference': 'correct_ref127'},
             ['match order returned None'],
             False,
             True,
             ),
        )
    )
    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('payments.api_clients.ok_pay.OkPayAPI._get_transaction_history')
    def test_release_flags(self,
                           # data_provider args
                           name,
                           order_modifiers,
                           order_modifiers_after_payment,
                           expected_parts_in_flag_val,
                           order_is_flagged,
                           user_verified_for_buy,
                           # stabs!
                           trans_history,
                           release_coins):

        trans_history.return_value = get_ok_pay_mock(
            data='transaction_history'
        )
        release_coins.return_value = \
            ('%06x' % random.randrange(16 ** 16)).upper()

        order = self.generate_orm_obj(
            Order,
            self.order_data,
            order_modifiers
        )[0]
        trans_history.return_value = create_ok_payment_mock_for_order(
            order
        )
        run_okpay.apply()
        payment = Payment.objects.get(order=order)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID, name)
        self.edit_orm_obj(order, order_modifiers_after_payment)

        with patch('payments.models.PaymentPreference.user_verified_for_buy',
                   new_callable=PropertyMock) as verified:
            verified.return_value = user_verified_for_buy
            self.release_task.apply()
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PAID, name)
        self.assertTrue(payment.flagged, name)
        if order_is_flagged:
            self.assertTrue(order.flagged, name)

        payment_flag = Flag.objects.filter(model_name=Payment.__name__,
                                           flagged_id=payment.pk).first()
        if order_is_flagged:
            self.assertTrue(order.flagged, name)
            order_flag = Flag.objects.filter(model_name=Order.__name__,
                                             flagged_id=order.pk).first()
            self.assertEqual(payment_flag.flag_val, order_flag.flag_val, name)
        for expec in expected_parts_in_flag_val:
            self.assertIn(expec, payment_flag.flag_val, name)
        with patch('orders.tasks.generic.buy_order_release.'
                   'BaseBuyOrderRelease.validate') as validate:
            # Check if order release is not attempted again
            self.release_task.apply()
            self.assertEqual(0, validate.call_count, name)
