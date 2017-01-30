from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'nexchange.settings')

app = Celery('nexchange')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings',
                       namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, 'task_summary')

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from orders.tasks.order_release import buy_order_release
    from accounts.tasks.generate_wallets import renew_cards_reserve
    from payments.tasks.generic.payeer import PayeerPaymentChecker
    from payments.tasks.generic.ok_pay import OkPayPaymentChecker

    okpay_import = OkPayPaymentChecker()
    payeer_imprt = PayeerPaymentChecker()

    sender.add_periodic_task(120.0, renew_cards_reserve.s(),
                             name='Renew cards reserve',
                             expires=10)

    sender.add_periodic_task(120.0, renew_cards_reserve.s(),
                             name='Renew cards reserve',
                             expires=10)

    sender.add_periodic_task(60.0, okpay_import.s(),
                             name='OkPay import',
                             expires=30)

    sender.add_periodic_task(60.0, payeer_imprt.s(),
                             name='Payeer import',
                             expires=30)

    sender.add_periodic_task(60.0, buy_order_release.s(),
                             name='Order release')


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
