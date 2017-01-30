from accounts.tests.base import TransactionImportBaseTestCase
import requests_mock
from accounts.utils import BlockchainTransactionImporter


class BlockchainImporterTestCase(TransactionImportBaseTestCase):

    def setUp(self):
        super(BlockchainImporterTestCase, self).setUp()
        self.importer = BlockchainTransactionImporter(self.address)
        self.run_method = self.importer.import_income_transactions

    @requests_mock.mock()
    def test_create_transactions_with_task(self, m):
        self.base_test_create_transactions_with_task(m, self.run_method)
