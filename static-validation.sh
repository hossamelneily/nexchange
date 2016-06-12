#!/bin/sh
# Auto-check for pep8 so I don't check in bad code

FILES_CACHED=$(git diff --cached --name-only --diff-filter=ACM | grep -e '\.py$')
FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')


OPTIONS="--ignore=F403"


if [ -n "$FILES" ] || [ -n "$FILES_CACHED" ] ; then
    echo "======================="
    echo "======= CHECKING FILES: $FILES $FILES_CACHED"
    echo "======================="
    flake8 $OPTIONS $FILES $FILES_CACHED
fi