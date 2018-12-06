from core.tests.base import OrderBaseTestCase
from core.tests.utils import enable_all_pairs
from payments.models import Payment, PaymentPreference
from orders.task_summary import buy_order_release_by_wallet_invoke as \
    wallet_release, \
    buy_order_release_by_reference_invoke as ref_release, \
    buy_order_release_reference_periodic as ref_periodic_release, \
    cancel_unpaid_order_periodic
from orders.models import Order
from core.models import Address, Currency, Pair, Transaction
from core.common.models import Flag
from decimal import Decimal
from datetime import timedelta, datetime
from freezegun import freeze_time
from unittest.mock import patch, PropertyMock
from copy import deepcopy
from django.db import transaction
from core.tests.utils import data_provider, get_ok_pay_mock,\
    create_ok_payment_mock_for_order
from django.contrib.auth.models import User
import random
import requests_mock
from payments.task_summary import run_okpay
from unittest import skip
from core.tests.base import UPHOLD_ROOT
from ticker.tests.base import TickerBaseTestCase
from nexchange.api_clients.uphold import UpholdApiClient
from orders.task_summary import release_retry_invoke
from orders.tasks.generic.retry_release import RetryOrderRelease
from django.conf import settings
from verification.models import Verification


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
        enable_all_pairs()
        currencies = Currency.objects.filter(is_crypto=False)
        for curr in currencies:
            curr.maximal_amount = 50000000
            curr.minimal_amount = 0.1
            curr.save()
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

    @skip('Test case operates with forbidden transitions i.e. '
          'INITIAL->RELEASED')
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
    @patch('orders.models.Order.calculate_quote_from_base')
    @patch('orders.models.instant.send_sms')
    @patch('orders.models.instant.send_email')
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
                      calculate_quote_from_base):

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
    @patch('orders.models.instant.send_sms')
    @patch('orders.models.instant.send_email')
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
        count = 0
        for status in statuses:
            if status == Order.RELEASED:
                count += 1
            order.status = status
            order.save()
            # Second save with same status change
            order.save()

            self.assertEqual(
                expect_notify_by_email * count, send_email.call_count,
                'user:{}, profile:{}'.format(user_props, profile_props)
            )
            self.assertEqual(
                expect_notify_by_phone * count, send_sms.call_count,
                'user:{}, profile:{}'.format(user_props, profile_props)
            )

    @patch('nexchange.api_clients.uphold.UpholdApiClient.release_coins')
    @patch('orders.models.instant.send_sms')
    @patch('orders.models.instant.send_email')
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
    @patch('orders.models.Order.coverable')
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
                           release_coins, coverable):

        trans_history.return_value = get_ok_pay_mock(
            data='transaction_history'
        )
        release_coins.return_value = \
            ('%06x' % random.randrange(16 ** 16)).upper(), True

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
        # self.assertEqual(order.status, Order.PAID, name)
        # FIXME: CANCEL because fiat needs refactoring
        self.assertEqual(order.status, Order.CANCELED)
        self.edit_orm_obj(order, order_modifiers_after_payment)

        Verification.objects.create(
            payment_preference=payment.payment_preference
        )
        with patch('payments.models.PaymentPreference.user_verified_for_buy',
                   new_callable=PropertyMock) as verified:
            verified.return_value = user_verified_for_buy
            ref_release.apply_async([payment.pk])
        order.refresh_from_db()
        payment.refresh_from_db()
        # self.assertEqual(order.status, Order.PAID, name)
        # FIXME: CANCEL because fiat needs refactoring
        self.assertEqual(order.status, Order.CANCELED)
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


@skip('Uphold is not working anymore')
class RetryReleaseTestCase(TickerBaseTestCase):

    def setUp(self):
        super(RetryReleaseTestCase, self).setUp()
        self.address = Address(
            type=Address.WITHDRAW,
            address='0x993cE7372Ed0621ddD4593ac3433E678236A496D')
        self.address.save()
        self.ETH = Currency.objects.get(code='ETH')
        self.client = UpholdApiClient()
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.withdraw_address = self.address
        self.order.save()
        self.tx_data = {
            'currency': self.order.pair.base,
            'amount': self.order.amount_base,
            'order': self.order,
            'address_to': self.order.withdraw_address,
            'type': Transaction.WITHDRAW
        }
        self.retry_release = RetryOrderRelease(api=self.client)

    @patch('orders.models.app.send_task')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_true(self, prepare_txn, execute_txn, send_task):
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        self.assertEqual(send_task.call_count, 1)

    @patch('orders.models.app.send_task')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_false(self, prepare_txn, execute_txn, send_task):
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'OK'}
        self.order.release(self.tx_data, api=self.client)
        self.assertEqual(send_task.call_count, 0)

    @patch('orders.models.app.send_task')
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_false_no_tx_id(self, prepare_txn, execute_txn,
                                          send_task):
        prepare_txn.return_value = ''
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        self.assertEqual(send_task.call_count, 0)

    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_x_times(self, prepare_txn, execute_txn):
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        txn = self.order.transactions.last()
        release_retry_invoke.apply([txn.pk])
        self.assertEqual(execute_txn.call_count,
                         settings.RETRY_RELEASE_MAX_RETRIES + 2)

    @data_provider(
        lambda: (
            ('Bad type', {'type': Transaction.DEPOSIT},
             {'success': False, 'retry': False}),
            ('tx_id exists', {'tx_id': '123sdf'},
             {'success': False, 'retry': False}),
            ('txn flagged', {'flagged': True},
             {'success': False, 'retry': False}),
            ('txn is_verified', {'is_verified': True},
             {'success': False, 'retry': False}),
            ('ok', {}, {'success': True, 'retry': False}),
        )
    )
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_class_errors_tx_data(self, name, tx_data_update,
                                                result, prepare_txn,
                                                execute_txn):
        tx_data = {
            'type': Transaction.WITHDRAW,
            'tx_id': '',
            'flagged': False,
            'is_verified': False
        }
        tx_data.update(tx_data_update)
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        execute_txn.return_value = {'code': 'ok'}
        txn = self.order.transactions.last()
        for attr, value in tx_data.items():
            setattr(txn, attr, value)
        txn.save()
        res = self.retry_release.run(txn.pk)
        self.assertEqual(res, result, name)

    @data_provider(
        lambda: (
            ('ok', {}, {'success': True, 'retry': False}),
            ('Bad amount', {'amount_base': 11.111},
             {'success': False, 'retry': False}),
            ('Bad currency', {'pair_id': 1},
             {'success': False, 'retry': False}),
            ('Bad status', {'status': Order.COMPLETED},
             {'success': False, 'retry': False}),
            ('Bad address', {'withdraw_address_id': 1},
             {'success': False, 'retry': False}),
        )
    )
    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_class_errors_order_data(self, name,
                                                   order_data_update,
                                                   result, prepare_txn,
                                                   execute_txn):
        self._create_order()
        self.order.status = Order.PRE_RELEASE
        self.order.withdraw_address = self.address
        self.order.save()
        self.tx_data.update({'order': self.order})
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        execute_txn.return_value = {'code': 'ok'}
        txn = self.order.transactions.last()
        for attr, value in order_data_update.items():
            setattr(self.order, attr, value)
        self.order.save()
        res = self.retry_release.run(txn.pk)
        self.assertEqual(res, result, name)

    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def test_retry_release_success(self, prepare_txn, execute_txn):
        prepare_txn.return_value = self.generate_txn_id()
        execute_txn.return_value = {'code': 'validation_failed'}
        self.order.release(self.tx_data, api=self.client)
        txn = self.order.transactions.last()
        self.assertFalse(txn.is_verified)
        self.assertEqual(execute_txn.call_count, 1)
        # First retry (success=False)
        res = self.retry_release.run(txn.pk)
        txn.refresh_from_db()
        self.assertEqual(res, {'success': False, 'retry': True})
        self.assertFalse(txn.is_verified)
        self.assertEqual(execute_txn.call_count, 2)
        execute_txn.return_value = {'code': 'ok'}
        # Second retry (success=True)
        res = self.retry_release.run(txn.pk)
        txn.refresh_from_db()
        self.assertEqual(res, {'success': True, 'retry': False})
        self.assertTrue(txn.is_verified)
        self.assertEqual(execute_txn.call_count, 3)
        # Third retry (stop because already released)
        res = self.retry_release.run(txn.pk)
        txn.refresh_from_db()
        self.assertEqual(res, {'success': False, 'retry': False})
        self.assertTrue(txn.is_verified)
        self.assertEqual(execute_txn.call_count, 3)


class CancelUnpaidOrdersTestCase(TickerBaseTestCase):

    def setUp(self):
        super(CancelUnpaidOrdersTestCase, self).setUp()
        self._create_order()
        self.order.status = Order.INITIAL
        self.order.save()

    def test_cancel_unpaid_orders_true(self):
        now = datetime.now() + timedelta(minutes=60)
        with freeze_time(now):
            self.assertTrue(self.order.unpaid_order_expired)
            cancel_unpaid_order_periodic.apply_async()
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, Order.CANCELED)

    def test_cancel_unpaid_orders_false(self):
        self.assertFalse(self.order.unpaid_order_expired)
        cancel_unpaid_order_periodic.apply_async()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.INITIAL)

    @patch('orders.models.Order._validate_status')
    def test_paid_unconfirmed_cancel_unpaid_orders_false(self,
                                                         validate_status):
        now = datetime.now() + timedelta(minutes=60)
        with freeze_time(now):
            for status in Order.STATUS_TYPES:
                self._create_order()
                if status[0] == Order.INITIAL:
                    continue
                self.order.status = status[0]
                self.order.save()
                self.assertFalse(self.order.unpaid_order_expired)
                cancel_unpaid_order_periodic.apply_async()
                self.order.refresh_from_db()
                self.assertEqual(self.order.status, status[0])
