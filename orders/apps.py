from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        import orders.signals.allocate_wallets  # noqa
        import orders.signals.notify_order  # noqa
