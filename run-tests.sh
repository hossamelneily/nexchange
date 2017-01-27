coverage erase
coverage run --source="." --omit="src/**" manage.py test -v=3 --pattern="**/tests/**/**/**.py" --settings=nexchange.settings_test
coverage report
coverage html -d cover