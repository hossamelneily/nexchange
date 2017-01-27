coverage erase
coverage run --source="." --omit="src/**" manage.py test -v=3 --pattern="**/tests/**py" --settings=nexchange.settings_test
coverage report
coverage html -d cover

#!/bin/bash

touch /root/test 2> /dev/null

if [ $? -eq 0 ]
then
   eho "tests passed"
   exit 0
else
  echo "Tests failed"
  exit 1
fi