from __future__ import absolute_import
from celery import Task
import logging
import sys


class BaseTask(Task):

    def __init__(self, *args, **kwargs):
        # Logging
        self.logger = logging.getLogger(
            self.__class__.__name__
        )

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s'
                                      ' - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        super(BaseTask, self).__init__(*args, **kwargs)
