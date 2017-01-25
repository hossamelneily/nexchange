from __future__ import absolute_import
from celery import Task
import logging


class BaseTask(Task):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(
            self.__class__.__name__
        )
        super(BaseTask, self).__init__(*args, **kwargs)
