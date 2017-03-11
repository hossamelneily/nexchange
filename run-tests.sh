#!/bin/bash

coverage erase
coverage run --source="." --omit="src/**" manage.py test --failfast -v=3 --pattern="test_*.py" --settings=nexchange.settings_test
TEST_STATUS_CODE=$?
coverage report
coverage html -d cover

#!/bin/bash

touch /root/test 2> /dev/null

if [ ${TEST_STATUS_CODE} -eq 0 ]
then
   echo "TESTS PASSED"
   exit 0
else
  echo "TESTS FAILED"
  exit 1
fi
