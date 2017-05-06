from core.tests.base import TransactionImportBaseTestCase
from accounts.tasks.generic.tx_importer.uphold import UpholdTransactionImporter


class UpholdImporterTestCase(TransactionImportBaseTestCase):

    def setUp(self):
        super(UpholdImporterTestCase, self).setUp()
        self.importer = UpholdTransactionImporter()
        self.run_method = self.importer.import_income_transactions

    def test_create_transactions_with_task(self):
        self.base_test_create_transactions_with_task(self.run_method)
