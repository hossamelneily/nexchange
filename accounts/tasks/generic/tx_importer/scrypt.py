from nexchange.api_clients.mixins import EthashRpcMixin, ScryptRpcMixin,\
    Blake2RpcMixin, ZcashRpcMixin
from .base import BaseTransactionImporter


class ScryptTransactionImporter(ScryptRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ScryptRpcMixin.__init__(self)


class ZcashTransactionImporter(ZcashRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ZcashRpcMixin.__init__(self)


class EthashTransactionImporter(EthashRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        EthashRpcMixin.__init__(self)


class Blake2TransactionImporter(Blake2RpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        Blake2RpcMixin.__init__(self)
