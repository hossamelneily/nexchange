from nexchange.utils import send_email
from django.conf import settings
from celery import shared_task
from .models import Verification
from django.urls import reverse
from orders.models import Order
from payments.models import Payment
from nexchange.utils import get_nexchange_logger


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def send_verification_upload_email(verification_id):
    ver = Verification.objects.get(pk=verification_id)
    _note = ver.note
    subject = 'KYC {} upload'.format(_note)
    order_ui_url = 'https://n.exchange/order/{}/'.format(_note)
    api_url = 'http://localhost:8000' \
        if settings.DEBUG else 'https://api.nexchange.io'
    order_api_url = '{}/en/api/v1/orders/{}/'.format(api_url, _note)
    kyc_api_url = '{}/en/api/v1/kyc/{}/'.format(api_url, _note)
    _kyc_path = reverse(
        'admin:verification_verification_change', args=[ver.pk]
    )
    kyc_admin_url = '{}{}'.format(api_url, _kyc_path)
    msg = \
        'Uploaded KYC documents:' \
        '<br><a href="{kyc_admin_url}">KYC admin</a>,' \
        '<br><a href="{kyc_api_url}">KYC API</a>,' \
        '<br><a href="{order_api_url}">Order API</a>,' \
        '<br><a href="{order_ui_url}">Order UI</a>'.format(
            kyc_admin_url=kyc_admin_url,
            kyc_api_url=kyc_api_url,
            order_api_url=order_api_url,
            order_ui_url=order_ui_url
        )
    send_email(
        settings.SUPPORT_EMAIL,
        subject=subject,
        msg=msg
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def notify_about_wrong_kyc_name_invoke(order_id):
    order = Order.objects.get(pk=order_id)
    _note = order.unique_reference
    subject = 'KYC {} name mismatch'.format(_note)
    api_url = 'http://localhost:8000' \
        if settings.DEBUG else 'https://api.nexchange.io'
    order_api_url = '{}/en/api/v1/orders/{}/'.format(api_url, _note)
    _kyc_path = reverse(
        'admin:verification_verification_changelist'
    ) + '?q={}'.format(_note)
    kyc_admin_url = '{}{}'.format(api_url, _kyc_path)
    msg = \
        'One or more <a href="{kyc_admin_url}">KYC</a> of ' \
        '<a href="{order_api_url}">Order</a> has wrong name.'.format(
            order_api_url=order_api_url,
            kyc_admin_url=kyc_admin_url
        )
    send_email(
        settings.SUPPORT_EMAIL,
        subject=subject,
        msg=msg
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_kyc_names_periodic():
    logger = get_nexchange_logger('Periodic Fiat Order Deposit Checker')
    pending_fiat_orders = Order.objects.filter(
        flagged=False, status=Order.PAID_UNCONFIRMED, exchange=False
    )
    for order in pending_fiat_orders:
        try:
            payment = order.payment_set.get(type=Payment.DEPOSIT)
            pref = payment.payment_preference
            has_kyc = pref.is_verified
            name_matches = pref.name_on_card_matches
            if has_kyc and not name_matches:
                notify_about_wrong_kyc_name_invoke.apply_async([order.pk])
        except Exception as e:
            logger.logger.info(e)
