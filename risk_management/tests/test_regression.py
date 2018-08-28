from ticker.tests.base import TickerBaseTestCase
from risk_management.models import Account, PortfolioLog
from decimal import Decimal
from core.models import Pair


class PropetiesTestCase(TickerBaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ENABLED_TICKER_PAIRS = [
            'BTCCOSS', 'BTCEUR', 'BTCUSD', 'BTCETH', 'COSSBTC', 'COSSETH',
            'ETHCOSS', 'COSSEUR', 'COSSUSD'
        ]
        super(PropetiesTestCase, cls).setUpClass()

    def test_disabled_ticker_portfolio(self):
        bal_coss = Account.objects.get(is_main_account=True,
                                       reserve__currency__code='COSS')
        bal_btc = Account.objects.get(is_main_account=True,
                                      reserve__currency__code='BTC')
        bal_btc.available = bal_btc.balance = Decimal(0.1)
        bal_btc.save()
        bal_coss.available = bal_coss.balance = Decimal(10000)
        bal_coss.save()
        coss_pair_names = [
            name for name in self.ENABLED_TICKER_PAIRS if 'COSS' in name
        ]
        for pair_name in coss_pair_names:
            pair = Pair.objects.get(name=pair_name)
            pair.disable_ticker = True
            pair.save()
        p_log = PortfolioLog()
        p_log.save()
        self.assertIsInstance(p_log.assets_str, str)
        self.assertIsInstance(p_log.total_btc, Decimal)
        self.assertIsInstance(p_log.total_eur, Decimal)
        self.assertIsInstance(p_log.total_eth, Decimal)
        self.assertIsInstance(p_log.total_usd, Decimal)

    def test_empty_portfolio(self):
        p_log = PortfolioLog()
        p_log.save()
        self.assertIsInstance(p_log.assets_str, str)
