from nexchange.utils import get_nexchange_logger
from django.contrib.auth.models import User
from core.signals.allocate_wallets import create_user_wallet
from core.models import Currency, AddressReserve


class BaseReserveMonitor:
    def __init__(self):
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )
        self.client = None
        self.wallet_name = None

    @classmethod
    def replace_wallet(cls, user, currency_code):
        currency = Currency.objects.get(code=currency_code)
        old_wallets = user.addressreserve_set.filter(
            user=user, currency=currency, disabled=False
        )
        for old_wallet in old_wallets:
            addresses = old_wallet.addr.all()
            for address in addresses:
                address.disabled = True
                address.user = None
                address.save()
            old_wallet.disabled = True
            old_wallet.user = None
            old_wallet.save()
        res = create_user_wallet(user, currency)
        return res

    def check_cards(self):
        all_crypto_curr = Currency.objects.filter(
            is_crypto=True, disabled=False)
        related_crypto_curr = all_crypto_curr.filter(
            wallet=self.wallet_name)
        user = User.objects.filter(profile__cards_validity_approved=False,
                                   is_staff=False).first()
        if user is None:
            user = User.objects.filter(address=None, is_staff=False).first()
        if user is None:
            return
        replace = False
        wallets = user.addressreserve_set.filter(disabled=False).exclude(
            currency__code='RNS')
        if len(related_crypto_curr) > len(wallets):
            replace = True
        else:
            for wallet in wallets:
                resp = self.client.api.get_card(wallet.card_id)
                if resp.get('message') == 'Not Found':
                    replace = True
                    break
        if replace:
            for curr in all_crypto_curr:
                res = self.replace_wallet(user, curr)
                if not res:
                    return
        profile = user.profile
        profile.cards_validity_approved = True
        profile.save()

    def resend_funds_to_main_card(self, card_id, curr_code):
        raise NotImplementedError

    def check_cards_balances(self):
        card = AddressReserve.objects.filter(
            user__isnull=False, need_balance_check=True, disabled=False,
            currency__wallet=self.wallet_name).first()
        if card is None:
            return
        self.resend_funds_to_main_card(card.card_id, card.currency.code)
        card.need_balance_check = False
        card.save()
