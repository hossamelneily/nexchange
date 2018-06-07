from nexchange.rpc.scrypt import ScryptRpcApiClient


class ZcashRpcApiClient(ScryptRpcApiClient):
    def __init__(self):
        super(ZcashRpcApiClient, self).__init__()
        self.related_nodes = ['rpc9']
        self.related_coins = ['ZEC']

    def backup_wallet(self, currency):
        self.call_api(currency.wallet, 'backupwallet', currency)
