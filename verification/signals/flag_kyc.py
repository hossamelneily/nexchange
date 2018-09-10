from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from verification.models import Verification


@receiver(m2m_changed, sender=Verification.category.through)
def video_category_changed(sender, **kwargs):
    action = kwargs.pop('action', None)
    instance = kwargs.pop('instance', None)
    if action == "post_add" and instance:
        f_categs = instance.category.filter(flagable=True)
        if f_categs:
            instance.flag(val='Contains flagable categories: {}'.format(
                [c.name for c in f_categs]
            ))
