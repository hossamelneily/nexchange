#!/bin/bash

# RU
python manage.py makemessages -d django -l ru
python manage.py makemessages -d djangojs -l ru

# EN
python manage.py makemessages -d django -l en
python manage.py makemessages -d djangojs -l en

# ES
python manage.py makemessages -d django -l es
python manage.py makemessages -d djangojs -l es

# Compile

python manage.py compilemessages