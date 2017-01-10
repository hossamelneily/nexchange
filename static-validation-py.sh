#!/bin/sh

# If we only check for '--cached', when one does 'git commit -a' static validation will be skipped...
FILES_PY=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')
FILES_JS=$(git diff --name-only --diff-filter=ACM | grep -e '\.js$')

OPTIONS="--ignore=F405  --exclude=*/migrations/*"


if [ -n "$FILES_PY" ] || [ -n "$FILES_CACHED_PY" ] ; then
    echo "======================="
    echo "======= CHECKING FILES: \n $FILES_PY $FILES_CACHED_PY"
    echo "======================="
    flake8 $OPTIONS $FILES_PY $FILES_CACHED_PY
else
    echo "======================="
    echo "======= No .py FILES TO COMMIT. SKIPPING FLASK8"
    echo "======================="
fi