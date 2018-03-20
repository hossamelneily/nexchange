#!/bin/bash
# ###
# This script is generate in deploy step and:
#   Exports variables
#   Apply migrations
#   Starts gunicorn
# ###
export DJANGO_SETTINGS_MODULE=nexchange.settings_dev
export GUNICORN_PORT=8000
export POSTGIS_ENV_POSTGRES_USER=nexchange
export POSTGIS_ENV_POSTGRES_PASSWORD=nexchange
export POSTGRES_USER=nexchange
export POSTGRES_PASSWORD=nexchange
export POSTGIS_ENV_POSTGRES_DB=nexchange
export POSTGIS_PORT_5432_TCP_ADDR=postgis
export POSTGIS_PORT_5432_TCP_PORT=5432
export NEW_RELIC_CONFIG_FILE=newrelic.ini
export NEW_RELIC_ENVIRONMENT=production
export NEW_RELIC_LICENSE_KEY=cf40949f459cfbd61b87e9d10673cc0bfe06f3aa
export REDIS_PORT_6379_TCP_ADDR=redis
export REDIS_PORT_6379_TCP_PORT=6379
# SECURITY SETTINGS
# DJ SECRET
export SECRET_KEY=''
# DEBUG
export DEBUG=
export CELERY_TASK_ALWAYS_EAGER=
export API1_IS_TEST=
export API1_ID_C1=cb970e70-7dfa-4d80-bfad-627c863c5e23
export API1_ID_C2=3ba17423-50d8-4f9c-88f1-ad84872dcfc4
export API1_ID_C3=32339baf-3854-4204-8d46-79b2d025b036
export API1_ID_C4=d6c3056c-65ec-4adc-b384-c97d279a8bd1
# YANDEX
export YANDEX_METRICA_ID_UK=42222484
export YANDEX_METRICA_ID_RU=42236989
# GA
export GOOGLE_ANALYTICS_PROPERTY_ID_UK=UA-85529010-3
export GOOGLE_ANALYTICS_PROPERTY_ID_RU=UA-85529010-2
# CAPTCHA
export RECAPTCHA_SITEKEY=
export RECAPTCHA_SECRET_KEY=
# PAYEER
export PAYEER_IPN_KEY=
export PAYEER_WALLET=
export PAYEER_ACCOUNT=
export PAYEER_API_ID=
export PAYEER_API_KEY=
# OKPAY
export OKPAY_WALLET=
export OKPAY_API_KEY=
# API1
export API1_PAT=
# API2
export API2_KEY=
export API2_SECRET=
# API3
export API3_KEY=
export API3_SECRET=
export API3_PUBLIC_KEY_C1=
# API4
export API4_KEY=
export API4_SECRET=
# API5
export API5_KEY=
export API5_SECRET=
# CARDPMT
export CARDPMT_API_ID=
export CARDPMT_API_PASS=
# SOFORT
export SOFORT_API_KEY=
# ADV CASH
export ADV_CASH_API_NAME=
export ADV_CASH_ACCOUNT_EMAIL=
export ADV_CASH_API_PASSWORD=
export ADV_CASH_SCI_NAME=
export ADV_CASH_SCI_PASSWORD=
export ADV_CASH_WALLET_USD=
export ADV_CASH_WALLET_EUR=
export ADV_CASH_WALLET_GBP=
export ADV_CASH_WALLET_RUB=
# ROBOKASSA
export ROBOKASSA_IS_TEST=0
export ROBOKASSA_LOGIN=
export ROBOKASSA_PASS1=
export ROBOKASSA_PASS2=
# Twilio
export TWILIO_ACCOUNT_SID=
export TWILIO_AUTH_TOKEN=
# Smtp
export EMAIL_HOST=
export EMAIL_HOST_USER=
export EMAIL_HOST_PASSWORD=
export EMAIL_PORT=587

#RPC1
export RPC_RPC1_USER=
export RPC_RPC1_PASSWORD=
export RPC_RPC1_PORT=
export RPC_RPC1_HOST=
export RPC_RPC1_K=

#RPC2
export RPC_RPC2_USER=
export RPC_RPC2_PASSWORD=
export RPC_RPC2_PORT=
export RPC_RPC2_HOST=
export RPC2_PUBLIC_KEY_C1=
export RPC_RPC2_K=


#RPC3
export RPC_RPC3_USER=
export RPC_RPC3_PASSWORD=
export RPC_RPC3_PORT=
export RPC_RPC3_HOST=
export RPC_RPC3_K=

#RPC4
export RPC_RPC4_USER=
export RPC_RPC4_PASSWORD=
export RPC_RPC4_PORT=
export RPC_RPC4_HOST=
export RPC_RPC4_K=

#RPC5
export RPC_RPC5_USER=
export RPC_RPC5_PASSWORD=
export RPC_RPC5_PORT=
export RPC_RPC5_HOST=
export RPC_RPC5_K=

#RPC6
export RPC_RPC6_USER=LTC
export RPC_RPC6_PASSWORD=
export RPC_RPC6_PORT=12005
export RPC_RPC6_HOST=
export RPC_RPC6_K=

#RPC7
export RPC_RPC7_USER=
export RPC_RPC7_PASSWORD=
export RPC_RPC7_PORT=
export RPC_RPC7_HOST=
export RPC_RPC7_K=

# SOCIAL login
export SOCIAL_AUTH_TWITTER_KEY=
export SOCIAL_AUTH_TWITTER_SECRET=
export SOCIAL_AUTH_FACEBOOK_KEY=
export SOCIAL_AUTH_FACEBOOK_SECRET=
export SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=
export SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=
export SOCIAL_AUTH_GITHUB_KEY=
export SOCIAL_AUTH_GITHUB_SECRET=
#
cd /pipeline/source
yes | apt install netcat
while ! nc -z postgis 5432
do
  >&2 echo "PostgreSQL '(postgis:5432)' not ready - waiting..."
  sleep 1;
done
echo "PostgreSQL '(postgis:5432)' is ready - moving on..."

sleep 5;

pip install -r requirements.txt

# Apply migrations
python manage.py migrate --settings=nexchange.settings_dev
# Import fixtures
python manage.py loaddata core/fixtures/market.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/currency_crypto.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/currency_fiat.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/country.json --settings=nexchange.settings_dev
python manage.py loaddata payments/fixtures/payment_method.json --settings=nexchange.settings_dev
python manage.py loaddata payments/fixtures/payment_preference.json --settings=nexchange.settings_dev
python manage.py loaddata referrals/fixtures/program.json --settings=nexchange.settings_dev
python manage.py loaddata risk_management/fixtures/reserve.json --settings=nexchange.settings_dev
python manage.py loaddata risk_management/fixtures/account.json --settings=nexchange.settings_dev
echo "To load the 'withdraw_address' fixture, uncomment the next line"
# python manage.py loaddata core/fixtures/withdraw_address.json
python manage.py loaddata core/fixtures/pairs_cross.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/pairs_btc.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/pairs_ltc.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/pairs_eth.json --settings=nexchange.settings_dev
python manage.py loaddata core/fixtures/pairs_rns.json --settings=nexchange.settings_dev

if [ ! -z 1 ] && [ 1 -eq 1 ]
then
  python manage.py loaddata articles/fixtures/articles.json --settings=nexchange.settings_dev
fi

# Create superuser
echo "from django.contrib.auth.models import User; User.objects.create_superuser('onit', 'weare@onit.ws','123q123q')" | python manage.py shell
#
# Start Cron Process
cron
# Fix orders and transactions
python manage.py migrate_order_statuses
python manage.py fix_replay_transactions
# Start celery stuff


adduser --disabled-password --gecos '' celery_user
celery worker -A nexchange --uid=celery_user -l info -c 4 &
celery beat -A nexchange -l info &
celery -A nexchange flower &
python /pipeline/source/manage.py runserver --settings=nexchange.settings_dev 0.0.0.0:8000