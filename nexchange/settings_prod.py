import dj_database_url

from nexchange.settings import *

DEBUG = True

ALLOWED_HOSTS = ['nexchange.co.uk', 'nexchange.ru',
                 'www.nexchange.co.uk', 'www.nexchange.ru']

DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))
}

# SECRET KEY
SECRET_KEY = os.getenv('SECRET_KEY')

GOOGLE_ANALYTICS_PROPERTY_ID = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID')
GOOGLE_ANALYTICS_DOMAIN = os.getenv('GOOGLE_ANALYTICS_DOMAIN')

# ReCaptcha
RECAPTCHA_SITEKEY = os.getenv('RECAPTCHA_SITEKEY')
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')

# OKPAY
OKPAY_WALLET = os.getenv('OKPAY_WALLET')
OKPAY_API_KEY = os.getenv('OKPAY_API_KEY')

# PAYEER
PAYEER_WALLET = os.getenv('PAYEER_WALLET')
PAYEER_API_KEY = os.getenv('PAYEER_API_KEY')


# UPHOLD
UPHOLD_USER = os.getenv('UPHOLD_USER')
UPHOLD_PASS = os.getenv('UPHOLD_PASS')


# Kraken
KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')


# ROBOKASSA
ROBOKASSA_IS_TEST = os.getenv('ROBOKASSA_IS_TEST', 0)
ROBOKASSA_LOGIN = os.getenv('ROBOKASSA_LOGIN')
ROBOKASSA_PASS1 = os.getenv('ROBOKASSA_PASS1')
ROBOKASSA_PASS2 = os.getenv('ROBOKASSA_PASS2')


# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

