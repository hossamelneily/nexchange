from nexchange.utils import OkPayAPI, PayeerAPIClient, get_nexchange_logger

from django.conf import settings

from orders.models import Order

ok_api = OkPayAPI(
    api_password=settings.OKPAY_API_KEY,
    wallet_id=settings.OKPAY_WALLET,
    url=settings.OKPAY_API_URL
)

payeer_api = PayeerAPIClient(
    account=settings.PAYEER_ACCOUNT,
    apiId=settings.PAYEER_API_ID,
    apiPass=settings.PAYEER_API_KEY,
    url=settings.PAYEER_API_URL
)


def send_money(order_pk):
    order = Order.objects.get(pk=order_pk)
    logger = get_nexchange_logger(__name__)
    res = {'error': 'Automatic payment is not available'}
    receiver = order.payment_preference.identifier
    amount = order.amount_quote
    currency_code = order.pair.quote.code
    ref = order.unique_reference
    if order.payment_preference.payment_method.name == 'Okpay':
        res = ok_api.send_money(
            receiver=receiver, currency=currency_code, amount=amount,
            comment=ref, invoice=ref, is_receiver_pays_fees=True
        )
    elif order.payment_preference.payment_method.name == 'Payeer Wallet':
        res = payeer_api.transfer_funds(
            currency_in=currency_code, currency_out=currency_code,
            amount=amount, receiver=receiver, comment=ref)
    if 'error' in res or 'errors' in res:
        logger.info(
            'Order {} cannot be paid automatically. Send money '
            'response: {}'.format(order, res))
        status = False
    else:
        status = True
    return status
