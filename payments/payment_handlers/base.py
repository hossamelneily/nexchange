from orders.models import Order
from payments.models import Payment
from nexchange.utils import get_nexchange_logger


class BasePaymentHandler:

    def __init__(self):
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )

    def register_payment(self, order_pk, **kwargs):
        order = Order.objects.get(pk=order_pk, status=Order.INITIAL)
        res = self._register_payment(order, **kwargs)
        return res

    def confirm_payment(self, payment_pk, **kwargs):
        payment = Payment.objects.get(pk=payment_pk)
        return self._confirm_payment(payment, **kwargs)
