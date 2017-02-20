from __future__ import absolute_import
from nexchange.celery import app
from nexchange.utils import get_nexchange_logger


class BaseTask(app.Task):

    def __init__(self, *args, **kwargs):
        # Logging
        self.logger = get_nexchange_logger(
            self.__class__.__name__,
            True,
            True
        )

        # override to make next tasks wait for the
        # end of the execution of the current task
        self.immediate_apply = True
        self.next_tasks = set()
        super(BaseTask, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        self.apply_next_tasks()

    def add_next_task(self, task, args, kwargs={}):
        self.logger.info('{} added next task {}'.
                         format(self.__class__.__name__,
                                task.__class__.__name__))

        if self.immediate_apply:
            app.send_task(task, args=args, **kwargs)

        else:
            self.next_tasks.add((task, args,))

    def apply_next_tasks(self):
        for task, args in self.next_tasks:
            app.send_task(task, args=args)
