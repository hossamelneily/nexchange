#!/bin/sh

FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')
if [ -n "$FILES" ]; then
    echo "======= RUNNING STATIC FILES VALIDATION"
    wercker build --direct-mount --pipeline static-validation
    status=$?
else 
    echo "======= NO .py FILES ON THIS COMMIT"
fi

if [ "$status" == "0" ]; then
    echo "======= RUNNING APP TESTS"
    wercker build --direct-mount --pipeline tests
    status=$?
fi

exit $status

