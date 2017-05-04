"""
Django settings for nexchange project.

Generated by 'django-admin startproject' using Django 1.9.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import sys
from datetime import timedelta

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
import dj_database_url
import logging

# SECRET KEY TEST
SECRET_KEY = 'zsl4+4%(%=0@f*tkf0f2u%dt&v&h_-g5mw*o25i$480=3qcb2k'

DEFAULT_FROM_EMAIL = 'support@nexchange.co.uk'
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_DIR = os.path.dirname(__file__)

PROJECT_PATH = os.path.join(SETTINGS_DIR, os.pardir)
PROJECT_PATH = os.path.abspath(PROJECT_PATH)

TEMPLATE_PATH = os.path.join(PROJECT_PATH, 'templates')
TEMPLATE_PATH_APP = os.path.join(TEMPLATE_PATH, 'app')

STATIC_PATH = os.path.join(PROJECT_PATH, 'static')
STATIC_URL = '/static/'

API1_USER = ''
API1_PASS = ''

ADMINS = [
    ('Oleg', 'oleg@onit.ws'),
    ('Sarunas', 'sarunas@nexchange.co.uk')
]

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('ru', _('Russian')),
    ('en', _('English')),
    ('es', _('Spanish')),
    ('ca', _('Catalan')),
    ('zh-hans', _('Simplified Chinese')),
]


# CUSTOM SETTINGS
GATEWAY_RESOLVE_TIME = 5
TRANSACTION_IMPORT_TIME = 10

USER_SETS_WITHDRAW_ADDRESS_MEDIAN_TIME = 30
TICKER_INTERVAL = 60
PAYMENT_IMPORT_INTERVAL = 30
TICKER_CACHE_BACKEND = 'memory'
PAYMENT_WINDOW_SAFETY_INTERVAL = timedelta(seconds=60)
PAYMENT_DEFAULT_SEEK_INTERVAL = timedelta(hours=12)
SMS_TOKEN_VALIDITY = timedelta(minutes=5)
SMS_TOKEN_CHARS = '1234567890'
REFERRAL_CODE_LENGTH = 10
REFERRAL_CODE_CHARS = 'ABCDEFGIKJKLMNOPRSTXYZ1234567890'
SMS_MESSAGE_AUTH = _('Nexchange confirmation code: {}')
UNIQUE_REFERENCE_LENGTH = 5
UNIQUE_REFERENCE_MAX_LENGTH = 16
REFERENCE_LOOKUP_ATTEMPTS = 5
SMS_TOKEN_LENGTH = 4
PAYMENT_WINDOW = 60
MAX_EXPIRED_ORDERS_LIMIT = 3
REFERRAL_FEE = 2

NUMERIC_INTERNATIONAL_PREFIX = '00'
PLUS_INTERNATIONAL_PREFIX = '+'

MIN_REQUIRED_CONFIRMATIONS = 4

PHONE_START_SHOW = 4
PHONE_END_SHOW = 4
PHONE_HIDE_PLACEHOLDER = '*'

REFERRER_GET_PARAMETER = 'ref'
REFERRAL_SESSION_KEY = REFERRER_GET_PARAMETER
REFERRAL_TOKEN_CHARS = REFERRAL_CODE_CHARS

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'nexchange.dev'
]

ALLOWED_IMAGE_FILE_EXTENSIONS = ['.jpg', '.png', '.pdf']


# Application definition

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'bootstrap3',
    'rest_framework',
    'corsheaders',
    'core',
    'ticker',
    'accounts',
    'orders',
    'referrals',
    'payments',
    'articles',
    'verification',
    'session_security',
    'axes',
    'nexchange',
    'support',
    'loginurl',
    'social_django',
]


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'loginurl.backends.LoginUrlBackend',
)


SITE_ID = 1

ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx?" \
                "isTest={0}&MerchantLogin={1}&" \
                "OutSum={2}&InvId={3}&SignatureValue={4}&Culture=ru"

OKPAY_URL = 'https://www.okpay.com/en/account/login.html?verification={1}&' \
            'reference={2}&return_url={3}'
OKPAY_API_URL = 'https://api.okpay.com/OkPayAPI?singleWsdl'

PAYEER_API_URL = 'https://payeer.com/ajax/api/api.php'
PAYEER_IPS = ['185.71.65.92', '185.71.65.189', '149.202.17.210']


SOFORT_API_URL = 'https://api.sofort.com/api/xml'
SOFORT_USER_ID = '141789'
SOFORT_PROJECT_ID = '344411'
SOFORT_API_KEY = 'some_id'


CARDPMT_API_URL = 'https://gateway.cardpmt.com/api.cgi'
CARDPMT_API_ID = 'user'
CARDPMT_API_PASS = 'name'

CMSPAGES = {
    'ABOUTUS': [
        ('about_us', _('About Us')),
        ('careers', _('Careers')),
        ('press', _('Press')),
        ('conference', _('Conference')),
        ('legal_privacy', _('Legal & Privacy')),
        ('security', _('Security'))],
    'RESOURCES': [
        ('faq', _('FAQ')),
        # ('blog', _('Blog')),
        ('fees', _('Fees')),
        ('support', _('Support')),
        ('affiliates', _('Affiliate Program')),
        # ('trading_guide', _('Trading Guide'))
    ]
}

REDIS_ADDR = 'redis'
REDIS_PORT = '6379'
REDIS_SCHEME = 'redis://{}:{}/{}'
REDIS_URL_BROKER = REDIS_SCHEME.format(REDIS_ADDR, REDIS_PORT, 1)
REDIS_URL_RESULT = REDIS_SCHEME.format(REDIS_ADDR, REDIS_PORT, 2)
REDIS_URL_CACHE = REDIS_SCHEME.format(REDIS_ADDR, REDIS_PORT, 3)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_CACHE,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "nexchange"
    }
}


CELERY_BROKER_URL = REDIS_URL_BROKER
CELERY_RESULT_BACKEND = REDIS_URL_RESULT
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT = ['pickle', 'json']


CELERY_BEAT_SCHEDULE = {
    'renew_cards_reserve': {
        'task': 'accounts.task_summary.renew_cards_reserve_invoke',
        'schedule': timedelta(seconds=60),
    },
    'import_crypto_deposit_transactions': {
        'task': 'accounts.task_summary.import_transaction_deposit_crypto_invoke', # noqa
        'schedule': timedelta(seconds=60),
    },
    'check_okpay_payments': {
        'task': 'payments.task_summary.run_okpay',
        'schedule': timedelta(seconds=PAYMENT_IMPORT_INTERVAL),
    },
    'check_payeer_payments': {
        'task': 'payments.task_summary.run_payeer',
        'schedule': timedelta(seconds=PAYMENT_IMPORT_INTERVAL),
    },
    'check_sofort_payments': {
        'task': 'payments.task_summary.run_sofort',
        'schedule': timedelta(seconds=PAYMENT_IMPORT_INTERVAL),
    },
    'buy_order_release_reference_periodic': {
        'task': 'orders.task_summary.buy_order_release_reference_periodic',
        'schedule': timedelta(seconds=30),
    },
    'exchange_order_release_periodic': {
        'task': 'orders.task_summary.exchange_order_release_periodic',
        'schedule': timedelta(seconds=30),
    },
    'checker_transactions': {
        'task': 'accounts.task_summary.update_pending_transactions_invoke',
        'schedule': timedelta(seconds=60),
    },
    'get_all_enabled_tickers': {
        'task': 'ticker.task_summary.get_all_tickers',
        'schedule': timedelta(seconds=TICKER_INTERVAL),
    },
}

TASKS_TIME_LIMIT = 30

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'session_security.middleware.SessionSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'referrals.middleware.ReferralMiddleWare',
    'core.middleware.TimezoneMiddleware',
    'core.middleware.LastSeenMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware'

]

ROOT_URLCONF = 'nexchange.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_PATH, TEMPLATE_PATH_APP],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'core.context_processors.google_analytics',
                'core.context_processors.country_code',
                'core.context_processors.recaptcha',
                'articles.context_processors.cms',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                # 'django.core.context_processors.request'
            ],
        },
    },
]


WSGI_APPLICATION = 'nexchange.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# defined by env specific configuration
user = os.getenv('POSTGIS_ENV_POSTGRES_USER', 'postgres')
password = os.getenv('POSTGIS_ENV_POSTGRES_PASSWORD', '')
host = os.getenv('POSTGIS_PORT_5432_TCP_ADDR', '')
port = os.getenv('POSTGIS_PORT_5432_TCP_PORT', '')
db = os.getenv('POSTGIS_ENV_POSTGRES_DB', 'nexchange')

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))

}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.'
        'password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.'
        'password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.'
        'password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.'
        'password_validation.NumericPasswordValidator',
    },
]

AUTH_PROFILE_MODULE = 'core.Profile'

# SOCIAL Login

AUTHENTICATION_BACKENDS = (
    'social_core.backends.github.GithubOAuth2',
    'social_core.backends.twitter.TwitterOAuth',
    'social_core.backends.facebook.FacebookOAuth2',
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

# LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_DIRS = (
    STATIC_PATH,
)

API1_IS_TEST = True
API1_ID_C1 = 'a1a88f60-7473-47e4-9b78-987daf198a5d'
API1_ID_C2 = ''
API1_ID_C3 = ''
CARDS_RESERVE_COUNT = 6

KRAKEN_PRIVATE_URL_API = "https://api.kraken.com/0/private/%s"
TWILIO_PHONE_FROM_UK = '+447481341915'
TWILIO_PHONE_FROM_US = '+16464612858'

LOGIN_REDIRECT_URL = reverse_lazy('orders.add_order')

GRAPH_HOUR_RANGES = [
    {'val': 0.05, 'name': 'Live'},
    {'val': 1, 'name': '1 Hour'},
    {'val': 4, 'name': '4 Hours'},
    {'val': 6, 'name': '6 Hours'},
    {'val': 8, 'name': '8 Hours'},
    {'val': 12, 'name': '12 Hours'},
    {'val': 16, 'name': '16 Hours'},
    {'val': 24, 'name': '1 Day'},
    {'val': 24 * 7, 'name': '7 Days'},
    {'val': 24 * 31, 'name': '1 Month'},
    {'val': 24 * 31 * 3, 'name': '3 Months'},
    {'val': 24 * 31 * 6, 'name': '6 Months'},
    {'val': 24 * 365, 'name': '1 Year'}
]
DEFAULT_HOUR_RANGE = 4

# to tests the API with localhost
CORS_ORIGIN_WHITELIST = (
    'nexchange.dev',
    'nexchange.co.uk',
    'nexchange.ru'
)


REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    )
}
# 12 months
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30 * 12


# https://docs.djangoproject.com/en/1.9/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SOCIAL = {
    'twitter': 'https://twitter.com/cryptoNexchange',
    'facebook': 'https://facebook.com/cryptoNexchange'
}

# NEW security measures

SESSION_SECURITY_WARN_AFTER = 1800
SESSION_SECURITY_EXPIRE_AFTER = 1860
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SECURITY_INSECURE = True
SESSION_SECURITY_PASSIVE_URLS = ["/en/api/v1/price/latest/",
                                 "/en/api/v1/price/history/",
                                 "/en/session_security/ping/",
                                 "https://mc.yandex.ru/webvisor/39575585",
                                 "https://mc.yandex.ru/watch/39575585"]

AXES_LOGIN_FAILURE_LIMIT = 10
AXES_USERNAME_FORM_FIELD = 'username'
AXES_COOLOFF_TIME = timedelta(minutes=30)

# SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True


# Redirect all logs to STDOUT where they will be picked `gelf` driver
# of docker compose
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'DEBUG',
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
BASIC_LOGGING_LEVEL = logging.DEBUG
CREDIT_CARD_IS_TEST = False
CARDPMT_TEST_MODE = False
