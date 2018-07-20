from django.conf import settings
from celery import shared_task
from newsletter.models import Submission


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def submit_newsletter():
    Submission.submit_queue()
