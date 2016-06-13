#!/bin/sh
# Auto-check for pep8 so I don't check in bad code

FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')

if [ -n "$FILES" ]; then
    echo "======================="
    echo "======= CHECKING FILES: $FILES"
    echo "======================="
fi