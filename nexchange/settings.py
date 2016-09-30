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
]


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
    'cms',
    'django_rq',
    'treebeard',
    'menus',
    'sekizai',
    'djangocms_admin_style',
    'djangocms_text_ckeditor',
    'easy_thumbnails',
    'filer',
    'mptt',
    'django.contrib.sites',
    'django.contrib.sitemaps',
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
    'referrals'
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

RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': 'some-password',
        'DEFAULT_TIMEOUT': 360,
    },
    'high': {
        'URL': os.getenv('REDISTOGO_URL',
                         'redis://localhost:6379/0'),
        'DEFAULT_TIMEOUT': 500,
    },
    'low': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    }
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
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'referrals.middleware.ReferralMiddleWare',
    'core.middleware.TimezoneMiddleware',
    # 'core.middleware.LastSeenMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
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
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',
            ],
        },
    },
]

CMS_TEMPLATES = (
    ('cms/cms_default.html', 'Default Template'),
    ('some_other.html', 'Some Other Template'),
)

CMS_PLACEHOLDER_CONF = {
    'content': {
        'name': _('Content'),
        'plugins': ['TextPlugin', 'LinkPlugin'],
        'default_plugins': [
            {
                'plugin_type': 'TextPlugin',
                'values': {
                    'body': '<p>Great websites :'
                            ' %(_tag_child_1)s and %(_tag_child_2)s</p>'
                },
                'children': [
                    {
                        'plugin_type': 'LinkPlugin',
                        'values': {
                            'name': 'django',
                            'url': 'https://www.djangoproject.com/'
                        },
                    },
                    {
                        'plugin_type': 'LinkPlugin',
                        'values': {
                            'name': 'django-cms',
                            'url': 'https://www.django-cms.org'
                        },
                    },
                ]
            },
        ]
    }
}

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


KRAKEN_PRIVATE_URL_API = "https://api.kraken.com/0/private/%s"
KRAKEN_API_KEY = "E6wsw96A+JsnY33k7SninDdg//JsoZSXcKBYtyrhUYlWyAxIeIIZn3ay"


KRAKEN_API_SIGN = "hLg6LkI+kHtlLJs5ypJ0GnInK0go/HM3xMSVIGgCTc" \
                  "aqoqy8FsTl1KVdgFfWCCfu7CMZeCW4qqMbATrzZaFtRQ=="


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
    DEFAULT_FROM_EMAIL = 'testing@example.com'

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
