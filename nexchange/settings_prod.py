import dj_database_url
from nexchange.settings import *

DEBUG = bool(os.getenv('DEBUG', False))
CELERY_TASK_ALWAYS_EAGER = bool(os.getenv('CELERY_TASK_ALWAYS_EAGER', False))
ALLOWED_HOSTS = [
    '192.168.1.104',
    'api.n.exchange',
    'api.nexchange.io',
    'nexchange.io',
    'www.nexchange.io',
]

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))
}

# SECRET KEY
SECRET_KEY = os.getenv('SECRET_KEY',
                       'zsl4+4%(%=0@f*tkf0f2u%dt&v&h_-g5mw*o25i$480=3qcb2k')

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

# API General
WALLET_TIMEOUT = 999


# API1
API1_PAT = os.getenv('API1_PAT')
API1_ID_C1 = os.getenv('API1_ID_C1')
API1_ID_C2 = os.getenv('API1_ID_C2')
API1_ID_C3 = os.getenv('API1_ID_C3')
API1_ID_C4 = os.getenv('API1_ID_C4')
API1_IS_TEST = bool(os.getenv('API1_IS_TEST', False))


# API2
API2_KEY = os.getenv('API2_KEY')
API2_SECRET = os.getenv('API2_SECRET')

# API3 TEST
API3_KEY = os.getenv('API3_KEY')
API3_SECRET = os.getenv('API3_SECRET')
API3_PUBLIC_KEY_C1 = os.getenv('API3_PUBLIC_KEY_C1')

# API4
API4_KEY = os.getenv('API4_KEY')
API4_SECRET = os.getenv('API4_SECRET')

# API5
API5_KEY = os.getenv('API5_KEY')
API5_SECRET = os.getenv('API5_SECRET')

# RPC
DEFAULT_RPC_USER = os.getenv('DEFAULT_RPC_USER')
DEFAULT_RPC_PASS = os.getenv('DEFAULT_RPC_PASS')
DEFAULT_RPC_HOST = os.getenv('DEFAULT_RPC_HOST')
RPC2_PUBLIC_KEY_C1 = os.getenv('RPC2_PUBLIC_KEY_C1')
RPC3_PUBLIC_KEY_C1 = os.getenv('RPC3_PUBLIC_KEY_C1')


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

LOG_EMAIL_HOST = os.getenv('LOG_EMAIL_HOST', EMAIL_HOST)
LOG_EMAIL_PORT = os.getenv('LOG_EMAIL_PORT', EMAIL_PORT)
LOG_EMAIL_USER = os.getenv('LOG_EMAIL_USER', EMAIL_HOST_USER)
LOG_EMAIL_PASSWORD = os.getenv('LOG_EMAIL_PASSWORD', EMAIL_HOST_PASSWORD)

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

# Caching
ORDER_CACHE_LIFETIME = os.getenv('ORDER_CACHE_LIFETIME', 60)
PRICE_CACHE_LIFETIME = os.getenv('PRICE_CACHE_LIFETIME', 30)
CURRENCY_CACHE_LIFETIME = os.getenv('CURRENCY_CACHE_LIFETIME', 60)
PAIR_CACHE_LIFETIME = os.getenv('PAIR_CACHE_LIFETIME', 60)

# statics
STATIC_ROOT = '/usr/share/nginx/html/static'
MEDIA_ROOT = '/usr/share/nginx/html/media'
MEDIA_URL = '/media/'

AXES_LOGIN_FAILURE_LIMIT = 10
AXES_USERNAME_FORM_FIELD = 'username'
AXES_COOLOFF_TIME = timedelta(minutes=5)


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
            'class': 'nexchange.utils.LogEmailHandler',
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

# Safe Charge
SAFE_CHARGE_ALLOWED_DMN_IPS = [
    '194.247.166.0-194.247.167.255',
    '195.28.166.0-195.28.166.255',
    '87.120.10.0-87.120.10.255'
]
SAFE_CHARGE_MERCHANT_ID = os.getenv('SAFE_CHARGE_MERCHANT_ID', '')
SAFE_CHARGE_MERCHANT_SITE_ID = os.getenv('SAFE_CHARGE_MERCHANT_SITE_ID', '')
SAFE_CHARGE_SECRET_KEY = os.getenv('SAFE_CHARGE_SECRET_KEY', '')
SAFE_CHARGE_TEST = False
SAFE_CHARGE_NOTIFY_URL = 'https://api.nexchange.io/en/payments/safe_charge/dmn/listen'  # noqa
SAFE_CHARGE_SUCCESS_URL = os.getenv('SAFE_CHARGE_SUCCESS_URL', 'https://n.exchange/order/{}')  # noqa
SAFE_CHARGE_ERROR_URL = os.getenv('SAFE_CHARGE_ERROR_URL', SAFE_CHARGE_SUCCESS_URL)  # noqa
SAFE_CHARGE_PENDING_URL = os.getenv('SAFE_CHARGE_PENDING_URL', SAFE_CHARGE_SUCCESS_URL)  # noqa
SAFE_CHARGE_BACK_URL = os.getenv('SAFE_CHARGE_BACK_URL', SAFE_CHARGE_SUCCESS_URL)  # noqa
