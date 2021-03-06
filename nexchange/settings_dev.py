from nexchange.settings_prod import *
from nexchange.settings import SAFE_CHARGE_ALLOWED_DMN_IPS

DEBUG = True

ADMINS = []


# Local and staging
INTERNAL_IPS = ('127.0.0.1', '192.168.99.100', '192.168.43.146')
ALLOWED_HOSTS += ('localhost', '192.168.43.146', 'nexchange.dev',
                  '207.154.223.232')
SESSION_COOKIE_DOMAIN = None
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]


DATABASES = {
    'default': dj_database_url.config(default='postgis://{}:{}@{}:{}/{}'
                                      .format(user, password, host, port, db))
}


def show_toolbar(request):
    return True


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_toolbar,
}

# Lockout only for 1 mins on dev
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = timedelta(seconds=30)
CELERY_ALWAYS_EAGER = False

# SECRET KEY TEST
SECRET_KEY = 'zsl4+4%(%=0@f*tkf0f2u%dt&v&h_-g5mw*o25i$480=3qcb2k'

# GA for staging and test
GOOGLE_ANALYTICS_PROPERTY_ID_UK = 'UA-83213781-4'
GOOGLE_ANALYTICS_PROPERTY_ID_RU = 'UA-83213781-4'

# YANDEX
YANDEX_METRICA_ID_RU = '42222484'
YANDEX_METRICA_ID_UK = '42222484'


# ReCaptcha TEST
RECAPTCHA_SITEKEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
RECAPTCHA_SECRET_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'

# OKPAY TEST
OKPAY_WALLET = ''
OKPAY_API_KEY = ''

# PAYEER TEST
PAYEER_WALLET = '287402376'
PAYEER_IPN_KEY = '12345'
PAYEER_ACCOUNT = 'P39962269'
PAYEER_API_ID = '291547231'
PAYEER_API_KEY = '12345'

# ADV CASH
ADV_CASH_API_NAME = 'test_api'
ADV_CASH_ACCOUNT_EMAIL = 'sarunas@onit.ws'
ADV_CASH_API_PASSWORD = 'HgkL1hcUhwUdx0V0Y1HOR7'
ADV_CASH_SCI_NAME = 'Test Sci'
ADV_CASH_SCI_PASSWORD = 'TLuY2zgQoZoy1TDW23tup3'
ADV_CASH_WALLET_USD = 'U481612001049'
ADV_CASH_WALLET_EUR = 'E116938354831'
ADV_CASH_WALLET_GBP = 'G858614605772'
ADV_CASH_WALLET_RUB = 'R093095975471'
ADV_CASH_WALLETS = [ADV_CASH_WALLET_USD, ADV_CASH_WALLET_EUR,
                    ADV_CASH_WALLET_GBP, ADV_CASH_WALLET_RUB]
# API General
WALLET_TIMEOUT = 999

# API1 TEST
API1_USER = 'sarunas@onit.ws'
API1_PASS = "jmCtC'b=FpA|ybP>Yn`W0t"
API1_PAT = '85eeff32b36839fbfa548420d9112056d3e12cf5'
API1_IS_TEST = False
API1_ID_C1 = 'e319c22c-a739-4344-b578-d69d26a98560'  # BTC
API1_ID_C2 = '7e8b0975-4b5c-4ff7-b7ce-ebd76e2ab963'  # LTC
API1_ID_C3 = 'aa37f5d5-79f8-4d04-a02b-203b886bae61'  # ETH
API1_ID_C4 = 'ad4a8829-76c2-4586-be0b-d76d523b0e42'  # BCH
API1_PAT = '85eeff32b36839fbfa548420d9112056d3e12cf5'
CARDS_RESERVE_COUNT = os.getenv('CARDS_RESERVE_COUNT', 2)

# API3 TEST
API3_KEY = 'f47d9dc75ad64c3ea8f7cd9140ffa300'
API3_SECRET = '8d69c0fa41974b74a8c9cba6d329630d'
API3_PUBLIC_KEY_C1 = 'D76VupJRKMCzc4144v41jV45oy1t6NTEBr'


# API4 TEST
API4_KEY = 'E8Z2NLMC-O02BBN8U-TIX2ITZY-2XJJD84I'
API4_SECRET = 'f34e35d5b5026e8df9a49f4c111da6311051bd0f7ec55c73c042282cc57e5f134b639349c13efaa0605e8770091fbf108ea030aa7c556d1fccb84070865a0e0a'  # noqa

# API5
API5_KEY = '13599f1590aa41ec885cdd835028c3d3'
API5_SECRET = 'iP0G4+AhsRuxf/pQkn2UUruSPtlAus71WXNiJAEI/aM='

# RPC
RPC2_PUBLIC_KEY_C1 = 'DB3exkR2vguwY82m27zhVrg14HbuXAHbmZ'


# ROBOKASSA TEST
ROBOKASSA_IS_TEST = 1
ROBOKASSA_LOGIN = 'nexchangeBTC'
ROBOKASSA_PASS1 = 'SBYcBnB8Oq63KK5UB7oC'
ROBOKASSA_PASS2 = 'vaXizy98NA4rOm8Mty6l'

# API2 TEST
API2_KEY = '7xfxJMXBgO9jE7EAWuoRGzSd9KiqaTMoHumujCfDFs5NousgjlpUBdqZ'
API2_SECRET = 'L3TKIhXDcC0WuHEQ+aU01h6E8po/tabEqCsS5Ra60Z8oE6lKa1W5UN2mnU+0nwR8DREkpVX/BaU1BQI5ydjXUg=='  # noqa

# BIN api
BINCODES_API_KEY = '68fce6fe3464c9fcd5dd10e923f62c53'

# PMT
CARDPMT_API_ID = 'user'
CARDPMT_API_PASS = 'name'


# Twilio TEST
TWILIO_ACCOUNT_SID = 'ACde6c35bc29e81275dee6b9e565377900'
TWILIO_AUTH_TOKEN = 'ce656e45dd35918a0e9e76b7a4cd1ec8'
TWILIO_PHONE_FROM_UK = '+15005550006'
TWILIO_PHONE_FROM_US = '+15005550006'


# Smtp
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_HOST_USER = \
    'postmaster@sandbox343da41cb0384e75a0671ecd188c213d.mailgun.org'
EMAIL_HOST_PASSWORD = '1b99036321092807df4993247427e235'
LOG_EMAIL_HOST = os.getenv('LOG_EMAIL_HOST', EMAIL_HOST)
LOG_EMAIL_PORT = os.getenv('LOG_EMAIL_PORT', EMAIL_PORT)
LOG_EMAIL_USER = os.getenv('LOG_EMAIL_USER', EMAIL_HOST_USER)
LOG_EMAIL_PASSWORD = os.getenv('LOG_EMAIL_PASSWORD', EMAIL_HOST_PASSWORD)

# SOCIAL login
SOCIAL_AUTH_TWITTER_KEY = 'xnXj4eEWnImoBMkkLClOaRZTn'
SOCIAL_AUTH_TWITTER_SECRET = \
    'mG4na89H7NXRuz4hkeztYdDpWR1WmIXmdGooZ2UBgsobJpiIOr'
SOCIAL_AUTH_FACEBOOK_KEY = '629049203964213'
SOCIAL_AUTH_FACEBOOK_SECRET = '52f49654fe01fc8dbdc0db5523fd92c6'
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = \
    '546911507928-ppinu0lnrhtlkvmpbers1cc8h930nfkq.apps.googleusercontent.com'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '_W2HnofO7Y_Xt4KKo4vey8Cj'
SOCIAL_AUTH_GITHUB_KEY = 'a3cfc6bebb2131c822eb'
SOCIAL_AUTH_GITHUB_SECRET = '2c5058a22a71f6b235f71d8dc3c461dd72596a02'

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

CARDPMT_TEST_MODE = False

# Confirmation code length (for telephone and email authentication)
CONFIRMATION_CODE_LENGTH = 4

# Safe Charge
SAFE_CHARGE_MERCHANT_ID = '5741690954528998130'
SAFE_CHARGE_MERCHANT_SITE_ID = '144073'
SAFE_CHARGE_SECRET_KEY = 'VidQsfiGeybqTOsPGP7kUcnb1yb62AkoRFNk24NupakkEGdZYZRvNncEkMUEP0uC'  # noqa
SAFE_CHARGE_TEST = True
SAFE_CHARGE_NOTIFY_URL = 'http://207.154.223.232:8000/en/payments/safe_charge/dmn/listen'  # noqa
SAFE_CHARGE_SUCCESS_URL = 'https://n.exchange/order/{}'
SAFE_CHARGE_ERROR_URL = SAFE_CHARGE_SUCCESS_URL
SAFE_CHARGE_PENDING_URL = SAFE_CHARGE_SUCCESS_URL
SAFE_CHARGE_BACK_URL = SAFE_CHARGE_SUCCESS_URL

# Idenfy settings
IDENFY_VOID_AFTER_MINUTES = 5
