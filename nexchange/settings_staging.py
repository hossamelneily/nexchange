import dj_database_url

from .settings_dev import *

DEBUG = True

ALLOWED_HOSTS += ['staging.nexchange.ru', 'staging.nexchange.co.uk']
