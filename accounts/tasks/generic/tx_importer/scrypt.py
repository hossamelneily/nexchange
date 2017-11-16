from nexchange.api_clients.mixins import EthashRpcMixin, ScryptRpcMixin
from .base import BaseTransactionImporter


class ScryptTransactionImporter(ScryptRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ScryptRpcMixin.__init__(self)


class EthashTransactionImporter(EthashRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        EthashRpcMixin.__init__(self)
