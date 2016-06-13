#!/bin/sh

FILES_CACHED=$(git diff --cached --name-only --diff-filter=ACM | grep -e '\.py$')

# If we only check for '--cached', when one does 'git commit -a' static validation will be skiped...
FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')

OPTIONS="--ignore=F403" 


if [ -n "$FILES" ] || [ -n "$FILES_CACHED" ] ; then
    echo "======================="
    echo "======= CHECKING FILES: $FILES $FILES_CACHED"
    echo "======================="
    flake8 $OPTIONS $FILES $FILES_CACHED
fi