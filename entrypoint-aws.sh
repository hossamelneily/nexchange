#!/bin/bash
# ###
# This script is generate in deploy step and:
#   Apply migrations
#   Starts gunicorn
# ###
python /usr/src/app/manage.py migrate
# Import fixtures
python /usr/src/app/manage.py loaddata core/fixtures/market.json
python /usr/src/app/manage.py loaddata core/fixtures/currency_algorithm.json
python /usr/src/app/manage.py loaddata core/fixtures/transaction_price.json
python /usr/src/app/manage.py loaddata core/fixtures/currency_crypto.json
python /usr/src/app/manage.py loaddata core/fixtures/currency_fiat.json
python /usr/src/app/manage.py loaddata core/fixtures/currency_tokens.json
python /usr/src/app/manage.py loaddata core/fixtures/country.json
python /usr/src/app/manage.py loaddata orders/fixtures/fee_source.json
python /usr/src/app/manage.py loaddata payments/fixtures/payment_method.json
python /usr/src/app/manage.py loaddata payments/fixtures/payment_preference.json
python /usr/src/app/manage.py loaddata referrals/fixtures/program.json
python /usr/src/app/manage.py loaddata risk_management/fixtures/reserve.json
python /usr/src/app/manage.py loaddata risk_management/fixtures/account.json
python /usr/src/app/manage.py loaddata verification/fixtures/document_type.json
python /usr/src/app/manage.py loaddata verification/fixtures/tier0.json
python /usr/src/app/manage.py loaddata verification/fixtures/tier1.json
python /usr/src/app/manage.py loaddata verification/fixtures/tier2.json
python /usr/src/app/manage.py loaddata verification/fixtures/tier3.json
echo "To load the 'withdraw_address' fixture, uncomment the next line"
# python manage.py loaddata core/fixtures/withdraw_address.json
python manage.py loaddata core/fixtures/pairs_cross.json
python manage.py loaddata core/fixtures/pairs_btc.json
python manage.py loaddata core/fixtures/pairs_ltc.json
python manage.py loaddata core/fixtures/pairs_eth.json
python manage.py loaddata core/fixtures/pairs_rns.json
python manage.py loaddata core/fixtures/pairs_bch.json
python manage.py loaddata core/fixtures/pairs_doge.json
python manage.py loaddata core/fixtures/pairs_xvg.json
python manage.py loaddata core/fixtures/pairs_nano.json
python manage.py loaddata core/fixtures/pairs_omg.json
python manage.py loaddata core/fixtures/pairs_bdg.json
python manage.py loaddata core/fixtures/pairs_eos.json
python manage.py loaddata core/fixtures/pairs_zec.json
python manage.py loaddata core/fixtures/pairs_usdt.json
python manage.py loaddata core/fixtures/pairs_xmr.json
python manage.py loaddata core/fixtures/pairs_kcs.json
python manage.py loaddata core/fixtures/pairs_bnb.json
python manage.py loaddata core/fixtures/pairs_knc.json
python manage.py loaddata core/fixtures/pairs_ht.json
python manage.py loaddata core/fixtures/pairs_bix.json
python manage.py loaddata core/fixtures/pairs_bnt.json
python manage.py loaddata core/fixtures/pairs_coss.json
python manage.py loaddata core/fixtures/pairs_cob.json
python manage.py loaddata core/fixtures/pairs_bmh.json
python manage.py loaddata core/fixtures/pairs_xrp.jsn
if [ ! -z $CMS_FROM_FIXTURE] && [ ${CMS_FROM_FIXTURE} -eq 1 ]
then
  python manage.py loaddata articles/fixtures/articles.json
fi
# Copy static data to nginx volume
cp -ra $WERCKER_OUTPUT_DIR/staticfiles/* /usr/share/nginx/html/static
cp -ra $WERCKER_OUTPUT_DIR/mediafiles/* /usr/share/nginx/html/media
#
# Create superuser
echo "from django.contrib.auth.models import User; User.objects.create_superuser('onit', 'weare@onit.ws','weare0nit')" | python manage.py shell
#
# Start Cron Process
# cron
# Fix orders and transactions
python manage.py migrate_order_statuses
python manage.py fix_replay_transactions
# Start celery stuff
# Protect staging by password from ENV
echo -n "$HTTP_AUTH_USER:" >> /nexchange/etc/nginx/.htpasswd
openssl passwd -apr1 $HTTP_AUTH_PASS >> /nexchange/etc/nginx/.htpasswd
adduser --disabled-password --gecos '' celery_user
celery worker -A nexchange --uid=celery_user -l info -c 4 &
celery beat -A nexchange -l info &
echo "Gunicorn start"
exec newrelic-admin run-program gunicorn --chdir /usr/src/app --name nexchange --bind 0.0.0.0:${GUNICORN_PORT} --workers 3 --log-level=info --access-logfile=- nexchange.wsgi:application "$@"
# Remove entrypoint in production to protect data
echo "from django.conf import settings; import os; int_debug = 1 if settings.DEBUG else 0; os.environ['PYDEBUG']=int_debug" | python manage.py shell
if ! [ $PYDEBUG ]; then
  rm $0
fi
