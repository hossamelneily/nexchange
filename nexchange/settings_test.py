from .settings import *

# When testing, use sqlite3 so the database is loaded in memory
# this will make tests run faster

RECAPTCHA_SITEKEY = '6LexXBEUAAAAANo9wLPdTo8ZBbSYsKQ7yNr0XBCY'
RECAPTCHA_SECRET_KEY = '6LexXBEUAAAAAEoMlZtt4IRNEvmLUsP0A478ZbI3'
RECAPTCHA_ALLOW_DUMMY_TOKEN = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

DEBUG = True
