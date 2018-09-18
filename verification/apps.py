from __future__ import unicode_literals

from django.apps import AppConfig


class VerificationConfig(AppConfig):
    name = 'verification'

    def ready(self):
        import verification.signals.add_kyc_groups  # noqa
        import verification.signals.flag_kyc  # noqa
        import verification.signals.notify_verification  # noqa
