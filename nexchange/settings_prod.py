from .settings import *
import dj_database_url


DEBUG = True

ALLOWED_HOSTS += ['nexchange.co.uk', 'nexchange.ru',
                  'www.nexchange.co.uk', 'www.nexchange.ru']

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))

}

AXES_COOLOFF_TIME = timedelta(minutes=15)
