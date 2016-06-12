#!/bin/sh
# Auto-check for pep8 so I don't check in bad code

FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')
OPTIONS="--ignore=F403"


if [ -n "$FILES" ]; then
    echo "======================="
    echo "======= CHECKING FILES: $FILES"
    echo "======================="
    flake8 $OPTIONS $FILES
else
    echo "======================="
    echo "======= No .py FILES TO COMMIT. SKIPING STATIC VALIDATION. "
    echo "======================="
fi