from django.db import models
from core.common.models import TimeStampedModel, NamedModel
from core.models import Currency
from decimal import Decimal


class SuspiciousTransactionCategory(TimeStampedModel, NamedModel):
    class Meta:
        verbose_name = 'Suspicious transaction category'
        verbose_name_plural = 'Suspicious transaction categories'

    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, null=True, blank=True)


class SuspiciousTransactions(TimeStampedModel):
    class Meta:
        verbose_name = 'Suspicious transaction'
        verbose_name_plural = 'Suspicious transactions'

    tx_id = models.CharField(max_length=100, default=None,
                             null=True, blank=True, db_index=True)
    currency = models.ForeignKey(Currency, null=True, blank=True, default=None,
                                 on_delete=models.DO_NOTHING)
    amount = models.DecimalField(null=False, max_digits=18, decimal_places=8,
                                 default=Decimal('0'), db_index=True)
    address_from = models.CharField(max_length=64, null=True, blank=True)
    address_to = models.CharField(max_length=64, null=True, blank=True)
    auto_comment = models.TextField(default=None, null=True, blank=True)
    human_comment = models.TextField(default=None, null=True, blank=True)
    approved = models.BooleanField(default=False)
    time = models.DateTimeField(null=True, blank=True)
    categories = models.ManyToManyField(SuspiciousTransactionCategory,
                                        blank=True)
