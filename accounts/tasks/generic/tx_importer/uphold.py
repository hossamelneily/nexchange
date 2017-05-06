from nexchange.api_clients.mixins import UpholdBackendMixin
from .base import BaseTransactionImporter


class UpholdTransactionImporter(BaseTransactionImporter, UpholdBackendMixin):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        UpholdBackendMixin.__init__(self)
