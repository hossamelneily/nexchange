from nexchange.api_clients.uphold import UpholdApiClient
from decimal import Decimal
from accounts.tasks.generic.addressreserve_monitor.base import \
    BaseReserveMonitor


class UpholdReserveMonitor(BaseReserveMonitor):
    def __init__(self):
        super(UpholdReserveMonitor, self).__init__()
        self.client = UpholdApiClient()
        self.wallet_name = 'api1'

    def resend_funds_to_main_card(self, card_id, curr_code):
        main_card_id = self.client.coin_card_mapper(curr_code)
        address_key = self.client.address_name_mapper(curr_code)

        card_data = self.client.api.get_card(card_id)
        main_card = self.client.api.get_card(main_card_id)
        if curr_code != card_data['currency'] or curr_code != main_card['currency']:  # noqa
            return
        address_to = main_card['address'][address_key]
        amount_to = card_data['balance']
        if Decimal(amount_to) == 0:
            return
        res = self.client.release_coins(curr_code, address_to, amount_to,
                                        card=card_id)
        return res
