from .settings import *
from nexchange import settings_dev
import logging

# fix send task always eager
# https://github.com/celery/celery/issues/581
# def send_task(name, args=(), kwargs={}, **opts):
#     task = current_app.tasks[name]
#     return task.apply(args, kwargs, **opts)
#
# if 'test' in sys.argv:
#     current_app.send_task = send_task
CELERY_BEAT_SCHEDULE.update(PAYMENT_CHECKER_TASKS)


SESSION_COOKIE_DOMAIN = None

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

# TODO: unit tests should not write to disk!
STATIC_ROOT = '/tmp/static'
MEDIA_ROOT = '/tmp/media'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEBUG = True

CELERY_TASK_ALWAYS_EAGER = True
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
OKPAY_API_KEY = ''
# PAYEER
PAYEER_WALLET = os.getenv('PAYEER_WALLET',
                          settings_dev.PAYEER_WALLET)
PAYEER_IPN_KEY = ''
PAYEER_ACCOUNT = os.getenv('PAYEER_ACCOUNT',
                           settings_dev.PAYEER_WALLET)
PAYEER_API_ID = ''
PAYEER_API_KEY = ''


# ADV CASH
ADV_CASH_API_NAME = ''
ADV_CASH_ACCOUNT_EMAIL = ''
ADV_CASH_API_PASSWORD = ''


# API1
API1_USER = os.getenv('API1_USER',
                      settings_dev.API1_USER)
API1_PASS = os.getenv('API1_PASS',
                      settings_dev.API1_PASS)
API1_IS_TEST = False
CARDS_RESERVE_COUNT = os.getenv('CARDS_RESERVE_COUNT',
                                settings_dev.CARDS_RESERVE_COUNT)


# API2
API2_KEY = ''
API2_SECRET = ''


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
TWILIO_PHONE_FROM_UK = '+15005550006'
TWILIO_PHONE_FROM_US = '+15005550002'


# Smtp
EMAIL_HOST = os.getenv('EMAIL_HOST', settings_dev.EMAIL_HOST)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', settings_dev.EMAIL_HOST_USER)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD',
                                settings_dev.EMAIL_HOST_PASSWORD)

AXES_COOLOFF_TIME = timedelta(seconds=10)
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': True,
            'include_html': True,
        },
    }
}
BASIC_LOGGING_LEVEL = logging.WARNING

# Confirmation code length (for telephone and email authentication)
CONFIRMATION_CODE_LENGTH = 4
PAIR_CACHE_LIFETIME = 3
