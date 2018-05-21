from risk_management.tests.base import RiskManagementBaseTestCase
from django.test import TestCase
from risk_management.models import Reserve, Account, Cover, PNL
from decimal import Decimal
from unittest.mock import patch
from core.tests.base import SCRYPT_ROOT
from core.models import Pair
from risk_management.task_summary import reserves_balance_checker_periodic
from collections import Counter
import json
from django.core.exceptions import ValidationError


class PropetiesTestCase(RiskManagementBaseTestCase):

    def test_str(self):
        reserves = Reserve.objects.all()
        accounts = Account.objects.all()
        for reserve in reserves:
            reserve.__str__()
        for account in accounts:
            account.__str__()

    def test_reserve_balance_without_accounts(self):
        reserve = Reserve(currency_id=1)
        reserve.save()
        balance = reserve.balance
        self.assertEqual(balance, Decimal('0.0'))

    def test_only_one_main_account(self):
        reserve = Reserve.objects.get(currency__code='XVG')
        main_account = Account.objects.get(is_main_account=True,
                                           reserve=reserve)
        other_accounts = Account.objects.filter(is_main_account=False,
                                                reserve=reserve)
        for account in other_accounts:
            account.is_main_account = True
            account.save()
            main_account.refresh_from_db()
            self.assertFalse(main_account.is_main_account)
            main_account = Account.objects.get(is_main_account=True,
                                               reserve=reserve)
            self.assertEqual(account, main_account)

    @patch(SCRYPT_ROOT + 'get_balance')
    @patch('nexchange.api_clients.bittrex.Bittrex.get_balance')
    def test_xvg_cover_amount_to_main_account(self, _get_balance,
                                              get_balance_scrypt):

        account = Account.objects.get(wallet='api3',
                                      reserve__currency__code='XVG')
        main_account = account.reserve.main_account
        pair = Pair.objects.get(name='XVGBTC')
        currency = pair.base
        amount_base = Decimal('12300')
        cover = Cover(account=account, amount_base=amount_base, pair=pair,
                      currency=currency)
        cover.save()

        # available_to_send >= need_to_send_additional
        balance_bittrex = amount_base + account.required_reserve \
            + main_account.required_reserve
        balance_main = Decimal('0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        reserves_balance_checker_periodic.apply_async()
        account.refresh_from_db()
        main_account.refresh_from_db()
        self.assertEqual(
            cover.amount_to_main_account,
            amount_base + main_account.required_reserve - balance_main
        )

        # available_to_send >= minimal_to_send_additional
        balance_bittrex = amount_base + account.required_reserve \
            + main_account.minimal_reserve
        balance_main = Decimal('0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        reserves_balance_checker_periodic.apply_async()
        account.refresh_from_db()
        main_account.refresh_from_db()
        self.assertEqual(
            cover.amount_to_main_account,
            amount_base + main_account.minimal_reserve - balance_main
        )
        # elif max_to_send >= minimal_to_send_additional
        balance_bittrex = amount_base + account.minimal_reserve \
            + main_account.minimal_reserve
        balance_main = Decimal('0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        reserves_balance_checker_periodic.apply_async()
        account.refresh_from_db()
        main_account.refresh_from_db()
        self.assertEqual(
            cover.amount_to_main_account,
            amount_base + main_account.minimal_reserve - balance_main
        )
        # else
        balance_bittrex = amount_base / Decimal('2')
        balance_main = Decimal('0')
        _get_balance.return_value = self._get_bittrex_get_balance_response(
            float(balance_bittrex), available=float(balance_bittrex)
        )
        get_balance_scrypt.return_value = balance_main
        reserves_balance_checker_periodic.apply_async()
        account.refresh_from_db()
        main_account.refresh_from_db()
        self.assertEqual(
            cover.amount_to_main_account,
            balance_bittrex - account.minimal_reserve
        )


class PnlTestCase(TestCase):

    def test_pnl_calc_example(self):
        pn = PNL(volume_ask=Decimal('32'), average_ask=Decimal('99.75'),
                 volume_bid=Decimal('13'), average_bid=Decimal('102.230769'),
                 exit_price=Decimal('99'))
        pn.save()
        self.assertEqual(pn._position, Decimal('19'))
        self.assertEqual(pn._realized_volume, Decimal('13'))
        self.assertEqual(pn._pnl_realized, Decimal('32.249997'))
        self.assertEqual(pn._pnl_unrealized, Decimal('-14.25'))
        self.assertEqual(pn._pnl, Decimal('17.999997'))
        self.assertIsInstance(pn.__str__(), str)


class FixtureTestCase(RiskManagementBaseTestCase):

    def setUp(self):
        super(FixtureTestCase, self).setUp()
        self.path = 'risk_management/fixtures/'

    def _test_fixture_pks(self, model):
        _data = []
        _data += json.loads(open('{}{}.json'.format(self.path, model)).read())
        _pks = [record['pk'] for record in _data]
        _counter = Counter(_pks)
        for key, value in _counter.items():
            if value != 1:
                raise ValidationError(
                    '{} pk {} repeated in fixtures!'.format(model, key)
                )

    def test_fixture_pks(self):
        for model in ['account', 'reserve']:
            self._test_fixture_pks(model)

    def test_check_reserve_levels_non_zero(self):
        reserves = Reserve.objects.all()
        fields = ['minimum_level', 'maximum_level', 'target_level',
                  'allowed_diff', 'minimum_main_account_level']
        for reserve in reserves:
            for field in fields:
                value = getattr(reserve, field)
                error_msg = '{} of {}(currency pk {}) is 0'.format(
                    field, reserve.currency.code, reserve.currency.pk
                )
                self.assertTrue(value > Decimal(0), error_msg)
