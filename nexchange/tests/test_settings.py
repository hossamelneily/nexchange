from unittest import TestCase, skip
from unittest.mock import patch
import os
from subprocess import call
import sys
from nexchange import settings, settings_prod


ENV_PARAMS = settings.__dict__.keys()
PROD_ENV_PARAMS = settings_prod.__dict__.keys()


class TestSettingsCase(TestCase):

    @patch.dict(os.environ, {key: '' for key in ENV_PARAMS})
    def test_empty_env_params_main(self):
        exit_status = call(['python', 'nexchange/settings.py'])
        if exit_status == 1:
            sys.exit(1)

    @skip('FIXME: cannot run this case because of circular imports, need to '
          'patch nexchange.__init__() so it would no import Celery')
    @patch.dict(os.environ, {key: '' for key in PROD_ENV_PARAMS})
    def test_empty_env_params_prod(self):
        exit_status = call(['python', 'nexchange/settings_prod.py'])
        if exit_status == 1:
            sys.exit(1)

    @patch.dict(
        os.environ, {'Empty': '', 'Two': '2'}
    )
    def test_get_env(self):
        self.assertEqual(settings_prod.get_env_param('Empty', '1'), '1')
        self.assertEqual(settings_prod.get_env_param('None', '1'), '1')
        self.assertEqual(settings_prod.get_env_param('Two', '1'), '2')
