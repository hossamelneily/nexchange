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

INSTALLED_APPS.append('django_nose')

# Use nose to run all tests
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Tell nose to measure coverage on the 'core' app
NOSE_ARGS = [
    '--with-coverage',
    '--cover-html',
    '--cover-package=core',
]
