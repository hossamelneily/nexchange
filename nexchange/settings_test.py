from .settings import *
from nexchange import settings_dev
# When testing, use sqlite3 so the database is loaded in memory
# this will make tests run faster

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

# TODO: unit tests should not write to disk!
STATIC_ROOT = '/tmp'
MEDIA_ROOT = '/tmp'

DEBUG = True


# SECRET KEY
# Allow dual run: CI server and local
SECRET_KEY = os.getenv('SECRET_KEY', settings_dev.SECRET_KEY)

GOOGLE_ANALYTICS_PROPERTY_ID_RU = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID_RU',
                                            settings_dev.
                                            GOOGLE_ANALYTICS_PROPERTY_ID_RU)
GOOGLE_ANALYTICS_PROPERTY_ID_UK = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID_UK',
                                            settings_dev.
                                            GOOGLE_ANALYTICS_PROPERTY_ID_UK)
# YANDEX
YANDEX_METRICA_ID_RU = os.getenv('YANDEX_METRICA_ID_RU',
                                 settings_dev.YANDEX_METRICA_ID_RU)
YANDEX_METRICA_ID_UK = os.getenv('YANDEX_METRICA_ID_UK',
                                 settings_dev.YANDEX_METRICA_ID_UK)

# ReCaptcha
RECAPTCHA_SITEKEY = os.getenv('RECAPTCHA_SITEKEY',
                              settings_dev.RECAPTCHA_SITEKEY)
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY',
                                 settings_dev.RECAPTCHA_SECRET_KEY)

# OKPAY
OKPAY_WALLET = os.getenv('OKPAY_WALLET',
                         settings_dev.OKPAY_WALLET)
OKPAY_API_KEY = os.getenv('OKPAY_API_KEY',
                          settings_dev.OKPAY_API_KEY)
# PAYEER
PAYEER_WALLET = os.getenv('PAYEER_WALLET',
                          settings_dev.PAYEER_WALLET)
PAYEER_IPN_KEY = os.getenv('PAYEER_IPN_KEY',
                           settings_dev.PAYEER_IPN_KEY)
PAYEER_ACCOUNT = os.getenv('PAYEER_ACCOUNT',
                           settings_dev.PAYEER_ACCOUNT)
PAYEER_API_ID = os.getenv('PAYEER_API_ID',
                          settings_dev.PAYEER_API_ID)
PAYEER_API_KEY = os.getenv('PAYEER_API_KEY',
                           settings_dev.PAYEER_API_KEY)

# UPHOLD
UPHOLD_USER = os.getenv('UPHOLD_USER',
                        settings_dev.UPHOLD_USER)
UPHOLD_PASS = os.getenv('UPHOLD_PASS',
                        settings_dev.UPHOLD_PASS)


# Kraken
KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY',
                           settings_dev.KRAKEN_API_KEY)
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET',
                              settings_dev.KRAKEN_API_SECRET)


# ROBOKASSA
ROBOKASSA_IS_TEST = os.getenv('ROBOKASSA_IS_TEST',
                              settings_dev.ROBOKASSA_IS_TEST)
ROBOKASSA_LOGIN = os.getenv('ROBOKASSA_LOGIN',
                            settings_dev.ROBOKASSA_LOGIN)
ROBOKASSA_PASS1 = os.getenv('ROBOKASSA_PASS1',
                            settings_dev.ROBOKASSA_PASS1)
ROBOKASSA_PASS2 = os.getenv('ROBOKASSA_PASS2',
                            settings_dev.ROBOKASSA_PASS2)


# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID',
                               settings_dev.TWILIO_ACCOUNT_SID)
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN',
                              settings_dev.TWILIO_AUTH_TOKEN)

# Smtp
EMAIL_HOST = os.getenv('EMAIL_HOST', settings_dev.EMAIL_HOST)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', settings_dev.EMAIL_HOST_USER)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD',
                                settings_dev.EMAIL_HOST_PASSWORD)
