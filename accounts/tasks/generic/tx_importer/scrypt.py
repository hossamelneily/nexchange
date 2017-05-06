from nexchange.api_clients.mixins import ScryptRpcMixin
from .base import BaseTransactionImporter


class ScryptTransactionImporter(BaseTransactionImporter, ScryptRpcMixin):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ScryptRpcMixin.__init__(self)
