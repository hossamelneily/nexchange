from nexchange.api_clients.uphold import UpholdApiClient
from accounts.tasks.generic.addressreserve_monitor.base import \
    BaseReserveMonitor


class UpholdReserveMonitor(BaseReserveMonitor):
    def __init__(self):
        super(UpholdReserveMonitor, self).__init__()
        self.client = UpholdApiClient()
        self.wallet_name = 'api1'
