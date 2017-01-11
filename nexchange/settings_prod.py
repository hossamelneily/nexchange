import dj_database_url

from nexchange.settings import *  # noqa: E401

DEBUG = True

ALLOWED_HOSTS += ['nexchange.co.uk', 'nexchange.ru',
                  'www.nexchange.co.uk', 'www.nexchange.ru']

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))

}


RECAPTCHA_SITEKEY = '6LdKThEUAAAAAPRj_x7i3GFBBDsDQcDjt3J4a_e8'
RECAPTCHA_SECRET_KEY = '6LdKThEUAAAAAHsVzEUp6z40iOeL5XpKL0F90GWE'
RECAPTCHA_ALLOW_DUMMY_TOKEN = False
