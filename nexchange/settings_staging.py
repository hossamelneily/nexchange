import dj_database_url

from .settings_dev import *

DEBUG = True

ALLOWED_HOSTS += ['staging.nexchange.ru', ]

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))

}
