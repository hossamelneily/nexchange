import dj_database_url
from nexchange.settings import *

DEBUG = bool(os.getenv('DEBUG', False))
CELERY_TASK_ALWAYS_EAGER = bool(os.getenv('CELERY_TASK_ALWAYS_EAGER', False))
ALLOWED_HOSTS = [
    'nexchange.co.uk',
    'nexchange.io',
    'staging.nexchange.io',
    'www.nexchange.co.uk',
    'www.nexchange.io',
]

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

# ADV CASH
ADV_CASH_API_NAME = os.getenv('ADV_CASH_API_NAME')
ADV_CASH_ACCOUNT_EMAIL = os.getenv('ADV_CASH_ACCOUNT_EMAIL')
ADV_CASH_API_PASSWORD = os.getenv('ADV_CASH_API_PASSWORD')
ADV_CASH_SCI_NAME = os.getenv('ADV_CASH_SCI_NAME')
ADV_CASH_SCI_PASSWORD = os.getenv('ADV_CASH_SCI_PASSWORD')
ADV_CASH_WALLET_USD = os.getenv('ADV_CASH_WALLET_USD')
ADV_CASH_WALLET_EUR = os.getenv('ADV_CASH_WALLET_EUR')
ADV_CASH_WALLET_GBP = os.getenv('ADV_CASH_WALLET_GBP')
ADV_CASH_WALLET_RUB = os.getenv('ADV_CASH_WALLET_RUB')
ADV_CASH_WALLETS = [ADV_CASH_WALLET_USD, ADV_CASH_WALLET_EUR,
                    ADV_CASH_WALLET_GBP, ADV_CASH_WALLET_RUB]

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

# SOFORT
SOFORT_API_KEY = os.getenv('SOFORT_API_KEY')

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

# SOCIAL login
SOCIAL_AUTH_TWITTER_KEY = os.getenv('SOCIAL_AUTH_TWITTER_KEY')
SOCIAL_AUTH_TWITTER_SECRET = os.getenv('SOCIAL_AUTH_TWITTER_SECRET')
SOCIAL_AUTH_FACEBOOK_KEY = os.getenv('SOCIAL_AUTH_FACEBOOK_KEY')
SOCIAL_AUTH_FACEBOOK_SECRET = os.getenv('SOCIAL_AUTH_FACEBOOK_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv(
    'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
SOCIAL_AUTH_GITHUB_KEY = os.getenv('SOCIAL_AUTH_GITHUB_KEY')
SOCIAL_AUTH_GITHUB_SECRET = os.getenv('SOCIAL_AUTH_GITHUB_SECRET')

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

# Confirmation code length (for telephone and email authentication)
CONFIRMATION_CODE_LENGTH = 4
