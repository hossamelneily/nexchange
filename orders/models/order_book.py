from core.common.models import SoftDeletableModel, TimeStampedModel, \
    UniqueFieldMixin, FlagableMixin
from audit_log.models import AuthStampedModel
from core.models import Pair
from django.db import models
from picklefield.fields import PickledObjectField
from orderbook import OrderBook as OrderBookObj


class OrderBook(TimeStampedModel, SoftDeletableModel,
                UniqueFieldMixin, FlagableMixin, AuthStampedModel):

    pair = models.OneToOneField(Pair, on_delete=models.DO_NOTHING)
    book_obj = PickledObjectField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.book_obj:
            self.book_obj = OrderBookObj()
        super(OrderBook, self).save(*args, **kwargs)

    def __str__(self, *args, **kwargs):
        return '{}'.format(self.pair.name)
