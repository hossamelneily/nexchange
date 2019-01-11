#!/bin/bash

coverage erase
DO_COVERAGE=0
OMIT="src/*,core/tests/test_api/*,core/tests/test_api_external/*,core/tests/test_noc/*"
while getopts ":c:t:" arg; do
  case $arg in
    t)
      SLASH="/"
      DOT="."
      DOT_PY=".py"
      TEST_PATH="${OPTARG//$SLASH/$DOT}"
      TEST_PATH="${TEST_PATH//$DOT_PY/}"
      echo $TEST_PATH
      ;;
    c)
      DO_COVERAGE=$OPTARG
      ;;
  esac
done
coverage run --source="." --omit=$OMIT -m pytest $TEST_PATH -c pytest-backend.ini
TEST_STATUS_CODE=$?
if [ ${DO_COVERAGE} -eq 1 ]
then
   COVERALLS_REPO_TOKEN=Y9cfC0hPig5JrjZe4zxgvgcuoZ3AmxZYo coveralls
   coverage report
   coverage html -d cover
fi

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
