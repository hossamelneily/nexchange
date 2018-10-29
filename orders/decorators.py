from functools import wraps
from nexchange.api_clients.factory import ApiClientFactory
from .models import Order, LimitOrder
from nexchange.utils import get_nexchange_logger

factory = ApiClientFactory()
logger = get_nexchange_logger('Orders Decorator logger')


def get_task(**kwargs):
    def _get_task(task_fn):
        @wraps(task_fn)
        def _wrapped_fn(search_val):
            Task = kwargs.get('task_cls')
            key = kwargs.get('key')
            lookup = {key: [search_val]}
            try:
                order = Order.objects.get(**lookup)
            except Order.DoesNotExist:
                order = None
            try:
                limit_order = LimitOrder.objects.get(**lookup)
            except LimitOrder.DoesNotExist:
                limit_order = None
            if bool(limit_order) == bool(order):
                logger.error(
                    '{} lookup for order found both Order and '
                    'LimitOrder'.format(lookup)
                )
                return
            _order = order if order else limit_order
            api = factory.get_api_client(_order.withdraw_currency.wallet)
            task = Task(api)
            return task_fn(search_val, task)

        return _wrapped_fn
    return _get_task
