#!/bin/bash

coverage erase
coverage run --source="." --omit="src/**,core/tests/test_api/*,core/tests/test_api_external/*,core/tests/test_noc/*" manage.py test --failfast --failfast -v=3 --pattern="test_*.py" --settings=nexchange.settings_test
TEST_STATUS_CODE=$?
while getopts ":c:" opt; do
    COVERALLS_REPO_TOKEN=Y9cfC0hPig5JrjZe4zxgvgcuoZ3AmxZYo coveralls
done
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
