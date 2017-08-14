from nexchange.utils import get_nexchange_logger
from payments.api_clients.ok_pay import OkPayAPI
from payments.api_clients.payeer import PayeerAPIClient
from payments.api_clients.adv_cash import AdvCashAPIClient

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

adv_cash_api = AdvCashAPIClient(
    api_name=settings.ADV_CASH_API_NAME,
    account_email=settings.ADV_CASH_ACCOUNT_EMAIL,
    api_password=settings.ADV_CASH_API_PASSWORD
)


def send_money(order_pk):
    status = False
    order = Order.objects.get(pk=order_pk)
    logger = get_nexchange_logger(__name__)
    res = {'error': 'Automatic payment is not available'}
    receiver = order.payment_preference.identifier
    amount = order.amount_quote
    currency_code = order.pair.quote.code
    ref = order.unique_reference
    method_name = order.payment_preference.payment_method.name
    if method_name == 'Okpay':
        res = ok_api.send_money(
            receiver=receiver, currency=currency_code, amount=amount,
            comment=ref, invoice=ref, is_receiver_pays_fees=True
        )
    elif method_name == 'Payeer Wallet':
        res = payeer_api.transfer_funds(
            currency_in=currency_code, currency_out=currency_code,
            amount=amount, receiver=receiver, comment=ref)
    elif method_name == 'Advanced Cash(advcash)':
        res = adv_cash_api.send_money(
            str(amount), currency_code, receiver_email=receiver, note=ref
        )
    if 'error' in res or 'errors' in res:
        msg = 'Order {} cannot be paid automatically. Send money ' \
              'response: {}'.format(order, res)
        logger.error(msg)
        order.flag(val=msg)
    elif 'status' in res:
        if res['status'] == 'OK':
            status = True
        else:
            msg = 'Order {} cannot be paid due to payment provider ' \
                  'error: {}'.format(order, res)
            logger.error(msg)
            order.flag(val=msg)
    else:
        status = True
    return status
