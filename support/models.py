from django.db import models
from django.contrib.auth.models import User
from orders.models import Order


class Support(models.Model):
    user = models.ForeignKey(User, verbose_name='user', null=True, blank=True)
    order = models.OneToOneField(Order, verbose_name='order',
                                 null=True, blank=True)
    name = models.CharField('Name', max_length=50)
    email = models.EmailField('Email')
    telephone = models.CharField('Telephone', max_length=50,
                                 null=True, blank=True)
    subject = models.CharField('Subject', max_length=50, null=True, blank=True)
    message = models.TextField('Message')
    is_resolved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Support"
        verbose_name_plural = "Support"
        ordering = ['-created']
