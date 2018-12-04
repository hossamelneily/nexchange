from core.common.models import TimeStampedModel
from django.db import models
from audit_log.models import AuthStampedModel
from core.common.models import NamedModel


class FeeSource(NamedModel):
    pass


class OrderFee(TimeStampedModel, AuthStampedModel):

    WITHDRAWAL = 'Withdrawal'
    PAYMENT_METHOD = 'Payment Method'
    MARKUP = 'Markup'

    amount_base = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True, null=True)
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8,
                                       blank=True, null=True)
    order = models.ForeignKey('orders.Order', null=False, blank=False,
                              on_delete=models.DO_NOTHING)
    fee_source = models.ForeignKey(FeeSource, null=True, blank=True,
                                   on_delete=models.DO_NOTHING)

    def __str__(self):
        pair = self.order.pair if self.order else None
        return \
            '{name} {ref} {amount_base} {base}/{amount_quote} {quote}'.format(
                name=self.fee_source if self.fee_source else None,
                ref=self.order.unique_reference if self.order else None,
                pair=self.order.pair if self.order else None,
                base=pair.base.code if pair else None,
                quote=pair.quote.code if pair else None,
                amount_quote=self.amount_quote,
                amount_base=self.amount_base
            )
