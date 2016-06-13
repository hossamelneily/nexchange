from .settings import *

# When testing, use sqlite3 so the satabase is loaded in memory for better performance
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

DEBUG = True
