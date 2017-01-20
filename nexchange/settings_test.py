from .settings import *

# When testing, use sqlite3 so the database is loaded in memory
# this will make tests run faster

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

DEBUG = True

<<<<<<< HEAD
SECRET_KEY = 'zsl4+4%(%=0@f*tkf0f2u%dt&v&h_-g5mw*o25i$480=3qcb2k'
=======
# Lockout only for 1 mins on dev
AXES_LOGIN_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = timedelta(minutes=5)
CELERY_ALWAYS_EAGER = True

# SECRET KEY TEST
SECRET_KEY = 'zsl4+4%(%=0@f*tkf0f2u%dt&v&h_-g5mw*o25i$480=3qcb2k'

# GA for staging and test
GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-83213781-1'
GOOGLE_ANALYTICS_DOMAIN = 'staging.nexchange.ru'

# ReCaptcha TEST
RECAPTCHA_SITEKEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
RECAPTCHA_SECRET_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'

# OKPAY TEST
OKPAY_WALLET = 'OK378628543'
OKPAY_API_KEY = 't6N7XcGz25Lmp9W8Krg4J3QeZ'

# UPHOLD TEST
UPHOLD_USER = 'kydim1312@yandex.ru'
UPHOLD_PASS = '$Kyzin1990'

# ROBOKASSA TEST
ROBOKASSA_IS_TEST = 1
ROBOKASSA_LOGIN = 'nexchangeBTC'
ROBOKASSA_PASS1 = 'SBYcBnB8Oq63KK5UB7oC'
ROBOKASSA_PASS2 = 'vaXizy98NA4rOm8Mty6l'

# Kraken TEST
KRAKEN_API_KEY = ''
KRAKEN_API_SIGN = ''


# Twilio TEST
TWILIO_ACCOUNT_SID = 'ACde6c35bc29e81275dee6b9e565377900'
TWILIO_AUTH_TOKEN = 'ce656e45dd35918a0e9e76b7a4cd1ec8'
>>>>>>> detele krakenx
