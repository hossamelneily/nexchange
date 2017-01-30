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

ADMINS = [
    ('Oleg', 'oleg@onit.ws'),
    ('Sarunas', 'sarunas.azna@gmail.com')
]

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('ru', 'Russian'),
    ('en', 'English'),
    ('es', 'Espanol'),
]


# CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

# CUSTOM SETTINGS
SMS_TOKEN_VALIDITY = timedelta(minutes=3)
SMS_TOKEN_CHARS = '1234567890'
REFERRAL_CODE_LENGTH = 10
REFERRAL_CODE_CHARS = 'ABCDEFGIKJKLMNOPRSTXYZ1234567890'
UNIQUE_REFERENCE_LENGTH = 5
REFERENCE_LOOKUP_ATTEMPTS = 5
SMS_TOKEN_LENGTH = 4
PAYMENT_WINDOW = 60
MAX_EXPIRED_ORDERS_LIMIT = 3
REFERRAL_FEE = 2

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
]


SITE_ID = 1

ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx?" \
                "isTest={0}&MerchantLogin={1}&" \
                "OutSum={2}&InvId={3}&SignatureValue={4}&Culture=ru"

OKPAY_URL = 'https://www.okpay.com/en/account/login.html?verification={1}&' \
            'reference={2}&return_url={3}'

PAYEER_API_URL = 'https://payeer.com/ajax/api/api.php'
PAYEER_IPS = ['185.71.65.92', '185.71.65.189', '149.202.17.210']

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
        # ('trading_guide', _('Trading Guide'))
    ]
}

REDIS_ADDR = 'redis'
REDIS_PORT = '6379'
REDIS_URL = 'redis://{}:{}/1'.format(REDIS_ADDR, REDIS_PORT)
CELERY_BROKER_URL = REDIS_URL


CELERY_BEAT_SCHEDULE = {
    'buy_order_release': {
        'task': 'orders.task_summary.buy_order_release',
        'schedule': timedelta(seconds=60),
    },
    'renew_cards_reserve': {
        'task': 'accounts.task_summary.update_pending_transactions',
        'schedule': timedelta(seconds=60),
    },
    'check_okpay_payments': {
        'task': 'payments.task_summary.run_okpay',
        'schedule': timedelta(seconds=60),
    },
    'check_payeer_payments': {
        'task': 'payments.task_summary.run_payeer',
        'schedule': timedelta(seconds=60),

    },
    'checker_transactions': {
        'task': 'accounts.task_summary.renew_cards_reserve',
        'schedule': timedelta(seconds=60),
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
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
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

UPHOLD_IS_TEST = True
UPHOLD_CARD_ID = 'a1a88f60-7473-47e4-9b78-987daf198a5d'
CARDS_RESERVE_COUNT = 6

KRAKEN_PRIVATE_URL_API = "https://api.kraken.com/0/private/%s"
TWILIO_PHONE_FROM = '+447481341915'

LOGIN_REDIRECT_URL = reverse_lazy('orders.add_order')

GRAPH_HOUR_RANGES = [
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
DEFAULT_HOUR_RANGE = 6

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

SESSION_SECURITY_WARN_AFTER = 540
SESSION_SECURITY_EXPIRE_AFTER = 600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SECURITY_PASSIVE_URLS = ["/en/api/v1/price/latest/",
                                 "/en/api/v1/price/history/",
                                 "/en/session_security/ping/",
                                 "https://mc.yandex.ru/webvisor/39575585",
                                 "https://mc.yandex.ru/watch/39575585"]

AXES_LOGIN_FAILURE_LIMIT = 6
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
            'level': 'WARNING',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
            'include_html': True,
        },
    }
}
