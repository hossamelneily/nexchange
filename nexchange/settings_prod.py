import dj_database_url
from nexchange.settings import *

DEBUG = bool(os.getenv('DEBUG', False))
CELERY_TASK_ALWAYS_EAGER = bool(os.getenv('CELERY_TASK_ALWAYS_EAGER', False))
ALLOWED_HOSTS = ['nexchange.co.uk', 'nexchange.ru',
                 'www.nexchange.co.uk', 'www.nexchange.ru',
                 'new.nexchange.co.uk']

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))
}

# SECRET KEY
SECRET_KEY = os.getenv('SECRET_KEY')

# GA
GOOGLE_ANALYTICS_PROPERTY_ID_RU = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID_RU')
GOOGLE_ANALYTICS_PROPERTY_ID_UK = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID_UK')

# YANDEX
YANDEX_METRICA_ID_RU = os.getenv('YANDEX_METRICA_ID_RU')
YANDEX_METRICA_ID_UK = os.getenv('YANDEX_METRICA_ID_UK')

# ReCaptcha
RECAPTCHA_SITEKEY = os.getenv('RECAPTCHA_SITEKEY')
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')

# OKPAY
OKPAY_WALLET = os.getenv('OKPAY_WALLET')
OKPAY_API_KEY = os.getenv('OKPAY_API_KEY')

# PAYEER
PAYEER_WALLET = os.getenv('PAYEER_WALLET')
PAYEER_IPN_KEY = os.getenv('PAYEER_IPN_KEY')
PAYEER_ACCOUNT = os.getenv('PAYEER_ACCOUNT')
PAYEER_API_ID = os.getenv('PAYEER_API_ID')
PAYEER_API_KEY = os.getenv('PAYEER_API_KEY')


# API1
API1_USER = os.getenv('API1_USER')
API1_PASS = os.getenv('API1_PASS')
API1_ID_C1 = os.getenv('API1_ID_C1')
API1_ID_C2 = os.getenv('API1_ID_C2')
API1_ID_C3 = os.getenv('API1_ID_C3')
API1_IS_TEST = bool(os.getenv('API1_IS_TEST', False))


# API2
API2_KEY = os.getenv('KRAKEN_API_KEY')
API2_SECRET = os.getenv('KRAKEN_API_SECRET')

# CARDPMT
CARDPMT_API_ID = os.getenv('CARDPMT_API_ID')
CARDPMT_API_PASS = os.getenv('CARDPMT_API_PASS')

# ROBOKASSA
ROBOKASSA_IS_TEST = os.getenv('ROBOKASSA_IS_TEST', 0)
ROBOKASSA_LOGIN = os.getenv('ROBOKASSA_LOGIN')
ROBOKASSA_PASS1 = os.getenv('ROBOKASSA_PASS1')
ROBOKASSA_PASS2 = os.getenv('ROBOKASSA_PASS2')


# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# Smtp
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_USE_TLS = True

# statics

STATIC_ROOT = '/usr/share/nginx/html/static'
MEDIA_ROOT = '/usr/share/nginx/html/media'
MEDIA_URL = '/media/'

AXES_LOGIN_FAILURE_LIMIT = 10
AXES_USERNAME_FORM_FIELD = 'username'
AXES_COOLOFF_TIME = timedelta(minutes=5)


# just add admin emailing
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'INFO',
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
            'level': 'DEBUG',
            'propagate': True,
            'include_html': True,
        },
    }
}
