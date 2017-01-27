coverage erase
coverage run --source="." --omit="src/**" manage.py test -v=3 --pattern="test_*.py"
coverage report
coverage html -d cover