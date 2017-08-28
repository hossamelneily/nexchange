#!/bin/bash

python manage.py test --failfast -v=3 --pattern="api_test*.py" --settings=nexchange.settings_test
