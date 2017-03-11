#!/bin/bash

python manage.py test --failfast -v=3 --pattern="selenium_test.py" --settings=nexchange.settings_test
