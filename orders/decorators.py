from functools import wraps
from nexchange.api_clients.factory import ApiClientFactory
from .models import Order

factory = ApiClientFactory()


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
                # TODO: Seperate validate from release
                # TODO: This is an ugly hack for PaymentReleaseByWallet
                # TODO: Where payment.order is absent
                payment_id = lookup.popitem()[1][0]
                try:
                    payment, order = Task.get_order(payment_id)
                except Order.DoesNotExist:
                    return

            api = factory.get_api_client(order.pair.base.wallet)
            task = Task(api)
            return task_fn(search_val, task)

        return _wrapped_fn
    return _get_task
