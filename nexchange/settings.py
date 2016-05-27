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
LANGUAGES = (
    ('ru', _('Rusian')),
    ('en', _('English')),

)

# CUSTOM SETTINS
PAYMENT_WINDOW = 60  # minutes
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'vyq9ufbalb_a19d#=27pvv_17*h2j%gykvp7*xe%=yit0#vhkb'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'bootstrap3',
    'rest_framework',
    'core',
    'ticker'
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
db = os.getenv('POSTGIS_ENV_POSTGRES_DB', 'photobase')

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))

}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_PROFILE_MODULE = "core.Profile"


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

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

UNIQUE_REFERENCE_LENGTH = 5

REFERENCE_LOOKUP_ATTEMPS = 5

MAIN_BANK_ACCOUNT = "XXXX12345-1233-22"

KRAKEN_PRIVATE_URL_API= "https://api.kraken.com/0/private/%s"
KRAKEN_API_KEY = "E6wsw96A+JsnY33k7SninDdg//JsoZSXcKBYtyrhUYlWyAxIeIIZn3ay"
KRAKEN_API_SIGN = "hLg6LkI+kHtlLJs5ypJ0GnInK0go/HM3xMSVIGgCTcaqoqy8FsTl1KVdgFfWCCfu7CMZeCW4qqMbATrzZaFtRQ=="

# Your Account SID from www.twilio.com/console
TWILIO_ACCOUNT_SID = 'AC0bd0fa94c8ca0084f3e512c741965364'
# Auth Token from www.twilio.com/console
TWILIO_AUTH_TOKEN = '811a1791827b6088fcaa2d5b43ccf017'
TWILIO_PHONE_FROM = '+447481341915'
# a small hack to avoid error while using my test account
TWILIO_ACCOUNT_VERIFIED_PHONES = ['+555182459515']

LOGIN_REDIRECT_URL = reverse_lazy('core.order')

'''
Configs for sending email for password reset.
Run 'python -m smtpd -n -c DebuggingServer localhost:1025' 
to see a dump of email that would be sent
'''
if DEBUG:
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = 'testing@example.com'
