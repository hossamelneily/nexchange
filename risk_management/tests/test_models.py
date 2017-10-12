from risk_management.tests.base import RiskManagementBaseTestCase
from risk_management.models import Reserve, Account


class PropetiesTestCase(RiskManagementBaseTestCase):

    def test_str(self):
        reserves = Reserve.objects.all()
        accounts = Account.objects.all()
        for reserve in reserves:
            reserve.__str__()
        for account in accounts:
            account.__str__()
