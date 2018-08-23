from core.models import TransactionApiMapper, Currency
from functools import wraps
from nexchange.utils import get_traceback, get_nexchange_logger
from .mappers import RpcMapper
from bitcoinrpc.authproxy import JSONRPCException


def track_tx_mapper(fn):
    @wraps(fn)
    def wrapper(self, node):
        self.mapper, created =\
            TransactionApiMapper.objects.get_or_create(node=node)
        self.start = self.mapper.start

        total_tx, filtered = fn(self, node)

        self.mapper.start = self.start + total_tx
        self.mapper.save()
        return total_tx, filtered
    return wrapper


def log_errors(fn):
    @wraps(fn)
    def wrapper(self, *args):
        logger = get_nexchange_logger(
            self.__class__.__name__
        )
        try:
            return fn(self, *args)
        except Exception as e:
            logger.error(
                'Exception {} Traceback {}'.format(
                    e, get_traceback()))

    return wrapper


def encrypted_endpoint(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            for arg in args:
                if isinstance(arg, Currency):
                    node = arg.wallet
                    break
                if arg[:3] == 'rpc':
                    node = arg
                    break
            api = self.get_api(node)
            rpc_pass = RpcMapper.get_pass(node)
            self.unlock(api, rpc_pass, **{'node': node})
            return fn(self, *args, **kwargs)
        except JSONRPCException as e:
            self.logger.error('JSON RPC ERROR HOST {} ERROR {}'
                              .format(self.rpc_endpoint, str(e)))
        finally:
            try:
                self.lock(api, **{'node': node})
                pass
            except JSONRPCException:
                msg = 'Unencrypted wallet was attempted ' \
                      'to be locked node: {}'.\
                    format(node)
                self.logger.error(msg)
    return wrapper
