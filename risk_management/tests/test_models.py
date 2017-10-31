from risk_management.tests.base import RiskManagementBaseTestCase
from risk_management.models import Reserve, Account
from decimal import Decimal


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
