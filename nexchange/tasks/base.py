from __future__ import absolute_import
from celery import Task
from nexchange.utils import get_nexchange_logger


class BaseTask(Task):

    def __init__(self, *args, **kwargs):
        # Logging
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )
        super(BaseTask, self).__init__(*args, **kwargs)
