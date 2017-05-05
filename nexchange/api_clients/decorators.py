from core.models import TransactionApiMapper
from functools import wraps
from nexchange.utils import get_traceback, get_nexchange_logger


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
