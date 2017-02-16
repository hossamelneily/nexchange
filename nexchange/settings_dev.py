from nexchange.settings_prod import *

DEBUG = True


# Local and staging
INTERNAL_IPS = ('127.0.0.1', '192.168.99.100')
ALLOWED_HOSTS += ('localhost',)
MIDDLEWARE_CLASSES += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INSTALLED_APPS += [
    'debug_toolbar',
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


def show_toolbar(request):
    return True


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_toolbar,
}

# Lockout only for 1 mins on dev
AXES_LOGIN_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = timedelta(minutes=5)
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
OKPAY_WALLET = 'OK702746927'
OKPAY_API_KEY = ''

# PAYEER TEST
PAYEER_WALLET = '287402376'
PAYEER_IPN_KEY = '12345'
PAYEER_ACCOUNT = 'P39962269'
PAYEER_API_ID = '291547231'
PAYEER_API_KEY = '12345'

# API1 TEST
API1_USER = 'kydim1312@yandex.ru'
API1_PASS = '$Kyzin1990'

# ROBOKASSA TEST
ROBOKASSA_IS_TEST = 1
ROBOKASSA_LOGIN = 'nexchangeBTC'
ROBOKASSA_PASS1 = 'SBYcBnB8Oq63KK5UB7oC'
ROBOKASSA_PASS2 = 'vaXizy98NA4rOm8Mty6l'

# API2 TEST
API2_KEY = ''
API2_SECRET = ''


# Twilio TEST
TWILIO_ACCOUNT_SID = 'ACde6c35bc29e81275dee6b9e565377900'
TWILIO_AUTH_TOKEN = 'ce656e45dd35918a0e9e76b7a4cd1ec8'
TWILIO_PHONE_FROM = '+15005550006'

# Smtp
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'onit_demo'
EMAIL_HOST_PASSWORD = 'Fo19F2fJe53BVPDnJl3DSZ'

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
            'level': 'INFO',
            'propagate': True,
            'include_html': True,
        }
    }
}
