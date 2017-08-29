from nexchange.utils import send_email
from django.conf import settings
from celery import shared_task
from .models import Support


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def send_support_email():
    ticket = Support.objects.latest('id')
    send_email(
        settings.SUPPORT_EMAIL,
        subject=ticket.subject,
        msg=ticket.message
    )
