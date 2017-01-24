from __future__ import absolute_import

import logging

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from core.models import Address, Transaction
from nexchange.utils import (CreateUpholdCard, check_transaction_blockchain,
                             check_transaction_uphold, release_payment,
                             send_email, send_sms, OkPayAPI, PayeerAPIClient)
from orders.models import Order
from payments.models import Payment, UserCards
from decimal import Decimal

logging.basicConfig(filename='payment_release.log', level=logging.INFO)


@shared_task
def buy_order_release():
    # TODO: iterate over payments instead, will be much faster
    for o in Order.objects.filter(is_paid=True,
                                  is_released=False,
                                  order_type=Order.BUY):
        if not o.withdraw_address:
            print("{} has now withdrawal address, moving on".
                  format(o.unique_reference))
            continue
        user = o.user
        profile = user.profile
        if settings.DEBUG:
            print("Look order {} ".format(o.unique_reference))
        p = Payment.objects.filter(user=user,
                                   amount_cash=o.amount_cash,
                                   payment_preference__payment_method=o.
                                   payment_preference.payment_method,
                                   is_redeemed=False,
                                   currency=o.currency).first()

        if p:
            print(o.withdraw_address)
            p.is_complete = True
            p.save()
            tx_id = release_payment(o.withdraw_address,
                                    o.amount_btc)

            if tx_id is None:
                continue

            print('tx id: {}'.format(tx_id))
            o.is_released = True
            o.save()

            p.is_redeemed = True
            p.save()

            adr = Address.objects.get(
                user=o.user, address=o.withdraw_address)

            t = Transaction(tx_id_api=tx_id, order=o, address_to=adr)
            t.save()

            title = _("Nexchange: Order released")
            msg = _("Your order {}:  is released").format(o.unique_reference)

            if settings.DEBUG:
                print(msg)

            # send sms depending on notification settings in profile
            if profile.notify_by_phone:
                phone_to = str(o.user.username)
                sms_result = send_sms(msg, phone_to)
                if settings.DEBUG:
                    print(str(sms_result))

            # send email
            if profile.notify_by_email:
                email = send_email(user.email, title, msg)
                email.send()

        elif settings.DEBUG:
            print('payment not found')


@shared_task
def sell_order_release():
    # TODO:
    # This the task to release FUNDS for clients that
    # SELL BTC or other coins to US
    # 1. Auto release funds when coins are credited
    # 2. Move funds from user card to our card
    # 3. Notify admin if auto payment is not available
    # for the payment preference that the user has selected.
    pass


@shared_task
def exchange_order_release():
    # TODO:
    # This the task to release COINS for clients that
    # EXCHANGE crypto-currencies, I.E. ETH to BTC
    # 1. Auto release funds when coins are credited
    # 2. Move funds from user card to our card
    # 3. Notify admin if auto payment is not available
    # for the payment preference that the user has selected.
    pass


@shared_task
def checker_transactions():
    for tr in Transaction.objects.\
            filter(Q(is_completed=False) | Q(is_verified=False)):
        order = tr.order
        profile = order.user.profile
        if settings.DEBUG:
            print("Look-up transaction with txid api {} ".format(tr.tx_id_api))
        if check_transaction_uphold(tr):
            tr.is_completed = True
            tr.save()
            order.is_completed = True
            order.save()

        if check_transaction_blockchain(tr):
            tr.is_verified = True
            tr.save()

            title = _("Nexchange: Order released")
            msg = _("Your order {}:  is released"). \
                format(tr.order.o.unique_reference)

            if profile.notify_by_phone:
                phone_to = str(tr.order.user.username)
                sms_result = send_sms(msg, phone_to)

                if settings.DEBUG:
                    print(str(sms_result))

            if profile.notify_by_email:
                email = send_email(tr.order.user.email, title, msg)
                email.send()

            if settings.DEBUG:
                print("Transaction {} is completed".format(tr.tx_id))


@shared_task
def renew_cards_reserve():
    if settings.DEBUG:
        print(
            settings.CARDS_RESERVE_COUNT,
            settings.UPHOLD_USER,
            settings.UPHOLD_PASS
        )
    api = CreateUpholdCard(settings.UPHOLD_IS_TEST)
    api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)
    currency = {'BTC': 'bitcoin', 'LTC': 'litecoin', 'ETH': 'ethereum'}
    for key, value in currency.items():
        count = UserCards.objects.filter(user=None, currency=key).count()
        while count < settings.CARDS_RESERVE_COUNT:
            new_card = api.new_card(key)
            if settings.DEBUG:
                print(new_card, key)
            address = api.add_address(new_card['id'], value)
            card = UserCards(card_id=new_card['id'],
                             currency=new_card['currency'],
                             address_id=address['id'])
            card.save()
            count = UserCards.objects.filter(user=None, currency=key).count()


@shared_task
def check_okpay_payments():
    api = OkPayAPI(
        api_password=settings.OKPAY_API_KEY,
        wallet_id=settings.OKPAY_WALLET
    )
    transactions = api.get_transaction_history()['Transactions']
    if settings.DEBUG:
        print(transactions)
    for trans in transactions:
        if trans['Status'] != 'Completed':
            continue
        if trans['Receiver']['WalletID'] != settings.OKPAY_WALLET:
            continue
        o_list = Order.objects.filter(
            (
                Q(unique_reference=trans['Comment']) |
                Q(unique_reference=trans['Invoice'])
            ),
            amount_cash=Decimal(trans['Net']),
            currency__code=trans['Currency']
        )
        if len(o_list) == 1:
            o = o_list[0]
            if o.currency.code != trans['Currency']:
                continue
            Payment.objects.get_or_create(
                amount_cash=Decimal(trans['Net']),
                user=o.user,
                order=o,
                reference=o.unique_reference,
                payment_preference=o.payment_preference,
                currency=o.currency
            )


@shared_task
def check_payeer_payments():
    api = PayeerAPIClient(
        account=settings.PAYEER_ACCOUNT,
        apiId=settings.PAYEER_API_ID,
        apiPass=settings.PAYEER_API_KEY,
        url=settings.PAYEER_API_URL
    )
    if settings.DEBUG:
        print(
            settings.PAYEER_ACCOUNT,
            settings.PAYEER_API_ID,
            settings.PAYEER_API_KEY,
            settings.PAYEER_API_URL
        )
    transactions = api.history_of_transactions()
    if settings.DEBUG:
        print(transactions)
    for trans in transactions:
        if settings.DEBUG:
            print(trans)
        trans = transactions[trans]
        if trans['status'] != 'success':
            continue
        if trans['to'] != settings.PAYEER_ACCOUNT:
            continue
        o_list = Order.objects.filter(
            (
                Q(unique_reference=trans['comment']) |
                Q(unique_reference=trans['shopOrderId'])
            ),
            amount_cash=float(trans['creditedAmount']),
            currency__code=trans['creditedCurrency']
        )
        if len(o_list) == 1:
            o = o_list[0]
            Payment.objects.get_or_create(
                amount_cash=Decimal(trans['creditedAmount']),
                user=o.user,
                order=o,
                reference=o.unique_reference,
                payment_preference=o.payment_preference,
                currency=o.currency
            )
