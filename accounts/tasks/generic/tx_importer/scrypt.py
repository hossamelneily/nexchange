from nexchange.api_clients.mixins import EthashRpcMixin, ScryptRpcMixin,\
    Blake2RpcMixin, ZcashRpcMixin, OmniRpcMixin, CryptonightRpcMixin, \
    RippleRpcMixin
from .base import BaseTransactionImporter


class ScryptTransactionImporter(ScryptRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ScryptRpcMixin.__init__(self)


class ZcashTransactionImporter(ZcashRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        ZcashRpcMixin.__init__(self)


class OmniTransactionImporter(OmniRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        OmniRpcMixin.__init__(self)


class EthashTransactionImporter(EthashRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        EthashRpcMixin.__init__(self)


class Blake2TransactionImporter(Blake2RpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        Blake2RpcMixin.__init__(self)


class CryptonightTransactionImporter(CryptonightRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        CryptonightRpcMixin.__init__(self)


class RippleTransactionImporter(RippleRpcMixin, BaseTransactionImporter):
    def __init__(self):
        BaseTransactionImporter.__init__(self)
        RippleRpcMixin.__init__(self)
