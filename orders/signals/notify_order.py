from django.db.models.signals import pre_save
from django.dispatch import receiver
from nexchange.utils import get_nexchange_logger
from orders.models import Order


logger = get_nexchange_logger('notify_order', True, True)


@receiver(pre_save, sender=Order)
def notify_orders(sender, instance=None, **kwargs):
    try:
        if instance is None:
            return
        if instance.pk is None:
            return
        status = instance.status
        if status in [Order.INITIAL, Order.CANCELED, Order.FAILED_RELEASE]:
            return
        status_before = Order.objects.get(pk=instance.pk).status
        if status == status_before:
            return
        instance.notify()
    except Exception as e:
        logger.error('Unable to send order notification. error: {}'.format(e))
