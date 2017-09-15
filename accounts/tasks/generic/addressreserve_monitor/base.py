from nexchange.utils import get_nexchange_logger
from django.contrib.auth.models import User
from core.models import Currency


class ReserveMonitor:
    def __init__(self, api, wallet=None):
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )
        self.wallet_name = wallet
        self.client = api

    def check_cards(self):
        # FIXME: must be redesigned to check one card at the time
        return
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
        wallets = user.addressreserve_set.filter(
            disabled=False, currency__wallet=self.wallet_name)
        if len(related_crypto_curr) > len(wallets):
            replace = True
        else:
            for wallet in wallets:
                valid = self.client.get_card_validity(wallet)
                if not valid:
                    replace = True
                    break
        if replace:
            for curr in all_crypto_curr:
                if curr.wallet == self.wallet_name:
                    client = self.client
                else:
                    client = self.api_factory.get_api_client(curr.wallet)
                res = client.replace_wallet(user, curr)
                if not res:
                    return
        profile = user.profile
        profile.cards_validity_approved = True
        profile.save()
