"""
Django settings for nexchange project.

Generated by 'django-admin startproject' using Django 1.9.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
import dj_database_url
from datetime import timedelta

DEFAULT_FROM_EMAIL = 'support@nexchange.ru'
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_DIR = os.path.dirname(__file__)

PROJECT_PATH = os.path.join(SETTINGS_DIR, os.pardir)
PROJECT_PATH = os.path.abspath(PROJECT_PATH)

TEMPLATE_PATH = os.path.join(PROJECT_PATH, 'templates')
TEMPLATE_PATH_APP = os.path.join(TEMPLATE_PATH, 'app')

STATIC_PATH = os.path.join(PROJECT_PATH, 'static')
STATIC_URL = '/static/'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('ru', 'Russian'),
    ('en', 'English'),
    ('es', 'Espanol'),
]


CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

# CUSTOM SETTINGS
SMS_TOKEN_VALIDITY = 30
SMS_TOKEN_CHARS = '1234567890'
REFERRAL_CODE_LENGTH = 10
REFERRAL_CODE_CHARS = 'ABCDEFGIKJKLMNOPRSTXYZ1234567890'
UNIQUE_REFERENCE_LENGTH = 5
REFERENCE_LOOKUP_ATTEMPTS = 5
SMS_TOKEN_LENGTH = 4
PAYMENT_WINDOW = 60  # minutes
MAX_EXPIRED_ORDERS_LIMIT = 3
REFERRAL_FEE = 2

MIN_REQUIRED_CONFIRMATIONS = 4

PHONE_START_SHOW = 4
PHONE_END_SHOW = 4
PHONE_HIDE_PLACEHOLDER = '*'

REFERRER_GET_PARAMETER = 'ref'
REFERRAL_SESSION_KEY = REFERRER_GET_PARAMETER
REFERRAL_TOKEN_CHARS = REFERRAL_CODE_CHARS

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'vyq9ufbalb_a19d#=27pvv_17*h2j%gykvp7*xe%=yit0#vhkb'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']


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
    'referrals',
    'djcelery',
    'session_security',
    'axes'
]

CMS_PERMISSION = False

SITE_ID = 1


ROBOKASSA_LOGIN = 'nexchangeBTC'
ROBOKASSA_PASS1 = 'SBYcBnB8Oq63KK5UB7oC'
ROBOKASSA_PASS2 = 'vaXizy98NA4rOm8Mty6l'
ROBOKASSA_IS_TEST = 1
ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx?" \
                "isTest={0}&MerchantLogin={1}&" \
                "OutSum={2}&InvId={3}&SignatureValue={4}&Culture=ru"

CMSPAGES = {
    'ABOUTUS': [('about_us', _('About Us')), ('careers', _('Careers')),
                ('press', _('Press')), ('conference', _('Conference')),
                ('legal_privacy', _('Legal & Privacy')),
                ('security', _('Security'))],
    'RESOURCES': [('faq', _('FAQ')), ('blog', _('Blog')),
                  ('fees', _('Fees')), ('support', _('Support')),
                  ('trading_guide', _('Trading Guide'))]
}

REDIS_ADDR = os.getenv('REDIS_PORT_6379_TCP_ADDR')
REDIS_PORT = os.getenv('REDIS_PORT_6379_TCP_PORT')
REDIS_URL = 'redis://{}:{}/1'.format(REDIS_ADDR, REDIS_PORT)


CELERYBEAT_SCHEDULE = {
    'check-payment': {
        'task': 'nexchange.tasks.payment_release',
        'schedule': timedelta(seconds=90),
    },
    'check-transactions': {
        'task': 'nexchange.tasks.checker_transactions',
        'schedule': timedelta(seconds=300),
    },
}


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
                'core.context_processors.cms',
                'django.core.context_processors.request'
            ],
        },
    },
]


CKEDITOR_SETTINGS = {
    'language': '{{ language }}',
    'toolbar': 'CMS',
    'skin': 'moono',
}

WSGI_APPLICATION = 'nexchange.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# defined by env specific configuration
user = os.getenv('POSTGIS_ENV_POSTGRES_USER', 'postgres')
password = os.getenv('POSTGIS_ENV_POSTGRES_PASSWORD', '')
host = os.getenv('POSTGIS_PORT_5432_TCP_ADDR', '')
port = os.getenv('POSTGIS_PORT_5432_TCP_PORT', '')
db = os.getenv('POSTGIS_ENV_POSTGRES_DB', 'photobase')

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

AUTH_PROFILE_MODULE = "core.Profile"


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

# LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/


STATIC_URL = '/static/'
STATIC_ROOT = '/usr/share/nginx/html/static'
MEDIA_ROOT = '/usr/share/nginx/html/media'
MEDIA_URL = '/media/'

STATICFILES_DIRS = (
    STATIC_PATH,
)

UPHOLD_USER = 'kydim1312@yandex.ru'
UPHOLD_PASS = '$Kyzin1990'
UPHOLD_IS_TEST = True
UPHOLD_CARD_ID = 'a1a88f60-7473-47e4-9b78-987daf198a5d'

KRAKEN_PRIVATE_URL_API = "https://api.kraken.com/0/private/%s"
KRAKEN_API_KEY = "E6wsw96A+JsnY33k7SninDdg//JsoZSXcKBYtyrhUYlWyAxIeIIZn3ay"
# KRAKEN_API_KEY = "0xq0CZSTPm373V/ranC6XQNqC29rt6nlkwe0TpS4GcV2A/wZbGRyjhG6"


KRAKEN_API_SIGN = "hLg6LkI+kHtlLJs5ypJ0GnInK0go/HM3xMSVIGgCTc" \
                  "aqoqy8FsTl1KVdgFfWCCfu7CMZeCW4qqMbATrzZaFtRQ=="

# KRAKEN_API_SIGN = "3IPxXgvFZwtQi85oxDUSjwcE2ESrUMCJYT3/
# VGRDp6uz0wivSXZ3mSj8Vm7hWDO8/MczvRRdi3ZWbGBlc//tXg=="


# KRAKEN_API_KEY = os.environ['KRAKEN_API_KEY']
# KRAKEN_API_SIGN = os.environ['KRAKEN_API_SECRET']
MAIN_DEPOSIT_ADDRESSES = [
    '38veBMhDeudaZs7zmDUy68cYJZupaHVBvR',
    '36Av3jUjCfRGQ7p9BTTfN7HEf5N3qqK18Q',
    '3KSZsqhHosSW9AAXedmUZ7s6W97xpj5ETX',
    '3AmU2SdVvucgX1eu4JR1sWWERmnWDXS3Dy',
    '3MTRfeeQb96ynFZqEV2EeMppgFu8cvowBj'
]

# Your Account SID from www.twilio.com/console
TWILIO_ACCOUNT_SID = 'AC0bd0fa94c8ca0084f3e512c741965364'
# Auth Token from www.twilio.com/console
TWILIO_AUTH_TOKEN = '811a1791827b6088fcaa2d5b43ccf017'
TWILIO_PHONE_FROM = '+447481341915'

LOGIN_REDIRECT_URL = reverse_lazy('core.order')

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

"""
Configs for sending email for password reset.
Run 'python -m smtpd -n -c DebuggingServer localhost:1025'
to see a dump of email that would be sent
"""
if DEBUG:
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS = False

# to test the API with localhost
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
    'twitter': 'https://twitter.com/nexchange.ru',
    'facebook': 'https://facebook.com/nexchange.ru'
}

BRAINTREE_API = {
    'SANDBOX': {
        'vault': True,
        'merchant_id': 'cx2ybd6krcd8v392',
        'public_key': 'pr3kwc58g6r2whd8',
        'private_key': '19e9a4db38b16bbea6034ccbcbed300f',
        'timeout': 60,
        'merchant_accounts': {
            'USD': 'pavlov',
            'EUR': 'euro',
            'RUB': 'cx2ybd6krcd8v392'
        }
    },
    'PRODUCTION': {
        'vault': True,
        'merchant_id': '2qjrf326433vgjcq',
        'public_key': 'vxbcfqt7mng73z3q',
        'private_key': '4ac4bbc0cf8efa7a1073ae31924e03a5',
        'timeout': 60,
        'merchant_accounts': {
            'USD': 'pavlov',
            'EUR': 'euro',
            'RUB': 'cx2ybd6krcd8v392'
        }
    }
}

BRAINTREE_API_MODE = 'SANDBOX'
# NEW security measures

SESSION_SECURITY_WARN_AFTER = 540
SESSION_SECURITY_EXPIRE_AFTER = 600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SECURITY_PASSIVE_URLS = ["/en/api/v1/price/latest/",
                                 "/en/api/v1/price/history/",
                                 "/en/session_security/ping/",
                                 "https://mc.yandex.ru/webvisor/39575585",
                                 "https://mc.yandex.ru/watch/39575585"]

