# flake8: noqa
from .tasks.generate_wallets import renew_cards_reserve
from .tasks.monitor_wallets import update_pending_transactions
from .tasks.monitor_wallets import import_transaction_deposit_crypto
from .tasks.generic.tx_importer.uphold import UpholdTransactionImporter
from .tasks.generic.tx_importer.scrypt import ScryptTransactionImporter
from nexchange.api_clients.uphold import UpholdApiClient
from django.conf import settings
from celery import shared_task
from django.contrib.auth.models import User
from core.signals.allocate_wallets import create_user_wallet
from core.models import Currency, AddressReserve
from decimal import Decimal


uphold_client = UpholdApiClient()

@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def renew_cards_reserve_invoke():
    return renew_cards_reserve()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def update_pending_transactions_invoke():
    return update_pending_transactions()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_renos_invoke():
    return import_transaction_deposit_crypto(ScryptTransactionImporter)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_uphold_invoke():
    return import_transaction_deposit_crypto(UpholdTransactionImporter)

all_importers = [
    import_transaction_deposit_uphold_invoke,
    import_transaction_deposit_renos_invoke
]


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def import_transaction_deposit_crypto_invoke():
    for importer in all_importers:
        importer.apply_async()


def replace_wallet(user, currency):
    currency = Currency.objects.get(code=currency)
    old_wallets = user.addressreserve_set.filter(user=user, currency=currency,
                                                 disabled=False)
    for old_wallet in old_wallets:
        addresses = old_wallet.addr.all()
        for address in addresses:
            address.disabled = True
            address.user = None
            address.save()
        old_wallet.disabled = True
        old_wallet.user = None
        old_wallet.save()
    create_user_wallet(user, currency)
    return True


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_cards():
    all_curr = Currency.objects.filter(is_crypto=True)
    crypto_curr = all_curr.exclude(code='RNS')
    user = User.objects.filter(profile__cards_validity_approved=False,
                               is_staff=False).first()
    if user is None:
        return
    replace = False
    wallets = user.addressreserve_set.filter(disabled=False).exclude(
        currency__code='RNS')
    if len(crypto_curr) > len(wallets):
        replace = True
    else:
        for wallet in wallets:
            resp = uphold_client.api.get_card(wallet.card_id)
            if resp.get('message') == 'Not Found':
                replace = True
                break
    if replace:
        for curr in all_curr:
            res = replace_wallet(user, curr)
            if not res:
                return
    profile = user.profile
    profile.cards_validity_approved = True
    profile.save()


def resend_funds_to_main_card(card_id, curr_code):
    if curr_code == 'ETH':
        main_card_id = settings.API1_ID_C3
        address_key = 'ethereum'
    elif curr_code == 'LTC':
        main_card_id = settings.API1_ID_C2
        address_key = 'litecoin'
    elif curr_code == 'BTC':
        main_card_id = settings.API1_ID_C1
        address_key = 'bitcoin'
    else:
        return

    card_data = uphold_client.api.get_card(card_id)
    main_card = uphold_client.api.get_card(main_card_id)
    if curr_code != card_data['currency'] or curr_code != main_card['currency']:  # noqa
        return
    address_to = main_card['address'][address_key]
    amount_to = card_data['balance']
    if Decimal(amount_to) == 0:
        return
    print(address_to)
    print(amount_to)
    txn_id = uphold_client.api.prepare_txn(card_id, address_to,
                                           amount_to, curr_code)
    res = uphold_client.api.execute_txn(card_id, txn_id)
    return res


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def check_cards_balances():
    card = AddressReserve.objects.filter(
        user__isnull=False, need_balance_check=True, disabled=False,
        currency__wallet='api1').first()
    if card is None:
        return
    try:
        resend_funds_to_main_card(card.card_id, card.currency.code)
    except Exception:
        pass
    card.need_balance_check = False
    card.save()

