#!/bin/sh
FILES_JS=$(git diff --name-only --diff-filter=ACM | grep -e '\.js$')
FILES_CACHED_JS=$(git diff --cached --name-only --diff-filter=ACM | grep -e '\.js$')
OPTIONS="--ignore=F405  --exclude=*/migrations/*"


if [ -n "$FILES_JS" ] || [ -n "$FILES_CACHED_JS" ] ; then
    echo "======================="
    echo "======= CHECKING FILES: \n $FILES_JS $FILES_CACHED_JS"
    echo "======================="
    npm run lint -s
else
    echo "======================="
    echo "======= No .js FILES TO COMMIT. SKIPPING JSHINT. "
    echo "======================="
fi