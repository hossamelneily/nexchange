from nexchange.utils import convert_camel_to_snake_case


def release_order(order):
    from core.models import Transaction
    from nexchange.api_clients.factory import ApiClientFactory

    order.refresh_from_db()
    if order.status >= order.RELEASED:
        return

    currency = order.withdraw_currency
    amount = order.withdraw_amount
    address = order.withdraw_address

    factory = ApiClientFactory()
    api = factory.get_api_client(currency.wallet)

    txid, b = api.release_coins(currency, address, amount)
    order.status = order.RELEASED
    order.save()
    tx, created = Transaction.objects.get_or_create(**{
        convert_camel_to_snake_case(order.__class__.__name__): order,
        'type': 'W',
        'address_to': address,
        'amount': amount
    })

    tx.tx_id = txid
    tx.save()
    order.refresh_from_db()
    tx.refresh_from_db()
    print(order)
    print(tx)
    print(tx.tx_id)
    return order, tx
