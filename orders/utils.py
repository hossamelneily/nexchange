from orders.models import Order


def release_order(o1):
    from core.models import Transaction
    from nexchange.api_clients.factory import ApiClientFactory

    o1.refresh_from_db()
    if o1.status >= o1.RELEASED:
        return

    factory = ApiClientFactory()
    api = factory.get_api_client(o1.pair.base.wallet)

    txid, b = api.release_coins(o1.pair.base, o1.withdraw_address,
                                o1.amount_base)
    o1.status = o1.RELEASED
    o1.save()
    tx, created = Transaction.objects.get_or_create(
        order=o1,
        type='W',
        address_to=o1.withdraw_address,
        amount=o1.amount_base
    )

    tx.tx_id = txid
    tx.save()
    o1.refresh_from_db()
    tx.refresh_from_db()
    print(o1)
    print(tx)
    print(tx.tx_id)
    return o1, tx


def refresh(idx, status):
    stuck = Order.objects.filter(status=status)
    return stuck[idx]
