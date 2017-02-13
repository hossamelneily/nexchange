from core.tests.base import TransactionImportBaseTestCase
from core.models import Address
import requests_mock
from accounts.task_summary import import_transaction_deposit_btc_invoke


class TransactionImportTaskTestCase(TransactionImportBaseTestCase):

    def setUp(self):
        super(TransactionImportTaskTestCase, self).setUp()
        self.run_method = import_transaction_deposit_btc_invoke.apply

    @requests_mock.mock()
    def test_create_transactions_with_task(self, m):
        self.base_test_create_transactions_with_task(m, self.run_method)

    @requests_mock.mock()
    def test_create_transactions_with_None_currency_address(self, m):
        self.address = Address(
            name='test address',
            address=self.wallet_address,
            user=self.user,
            type=Address.DEPOSIT
        )
        self.address.save()
        self.base_test_create_transactions_with_task(m, self.run_method)
