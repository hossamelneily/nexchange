#!/bin/sh

FILES_CACHED=$(git diff --cached --name-only --diff-filter=ACM | grep -e '\.py$')
FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')


if [ -n "$FILES" ] || [ -n "$FILES_CACHED" ] ; then
    wercker build --direct-mount --pipeline static-validation &&
        wercker build --direct-mount --pipeline tests
else
    echo "======================="
    echo "======= No .py FILES TO COMMIT. SKIPING STATIC VALIDATION. "
    echo "======================="
    wercker build --direct-mount --pipeline tests
fi
