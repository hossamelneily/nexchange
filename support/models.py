from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from core.common.models import IndexTimeStampedModel, UniqueFieldMixin
from django.utils.translation import ugettext_lazy as _
from orders.models import Order


class Support(IndexTimeStampedModel, UniqueFieldMixin):
    user = models.ForeignKey(User, verbose_name='user', null=True, blank=True,
                             on_delete=models.CASCADE)
    order = models.OneToOneField(Order, verbose_name='order',
                                 null=True, blank=True,
                                 on_delete=models.CASCADE)
    name = models.CharField(_('Name*'), max_length=50)
    email = models.EmailField(_('Email*'))
    telephone = models.CharField(_('Telephone'), max_length=50,
                                 null=True, blank=True)
    subject = models.CharField(_('Subject'), max_length=50,
                               null=True, blank=True)
    message = models.TextField(_('Message*'))
    comment = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    unique_reference = models.CharField(
        max_length=settings.UNIQUE_REFERENCE_MAX_LENGTH)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.unique_reference:
            self.unique_reference = \
                self.gen_unique_value(
                    lambda x: self.get_random_unique_reference(x),
                    lambda x: Order.objects.filter(unique_reference=x).count(),
                    settings.UNIQUE_REFERENCE_LENGTH
                )
        super(Support, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Support'
        verbose_name_plural = 'Support'
        ordering = ['-created_on']

    def get_user_orders(self):
        if self.user:
            return Order.objects.filter(user=self.user)
        return []

    @property
    def user_orders(self):
        return list(self.get_user_orders())
