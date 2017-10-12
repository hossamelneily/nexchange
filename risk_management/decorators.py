from nexchange.api_clients.factory import ApiClientFactory
from functools import wraps


factory = ApiClientFactory()


def get_task(**kwargs):
    def _get_task(task_fn):
        @wraps(task_fn)
        def _wrapped_fn(search_val):
            Task = kwargs.get('task_cls')
            task = Task()
            return task_fn(search_val, task)

        return _wrapped_fn
    return _get_task
