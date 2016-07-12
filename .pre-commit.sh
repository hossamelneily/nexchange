#!/bin/sh

RUNNING_CONTAINER=$(docker ps -q --filter "ancestor=pitervergara/geodjango:nexchange" --filter name="wercker-pipeline-" --filter status=running)

FILES_CACHED=$(git diff --cached --name-only --diff-filter=ACM | grep -e '\.py$')
FILES=$(git diff --name-only --diff-filter=ACM | grep -e '\.py$')


function use_running_container {
    
    docker exec -t ${RUNNING_CONTAINER} bash -c "cd /pipeline/source && ./static-validation.sh" &&
        docker exec -t ${RUNNING_CONTAINER} bash -c "cd /pipeline/source && DJANGO_SETTINGS_MODULE=nexchange.settings_test python manage.py test -v 3" &&
            docker exec -t ${RUNNING_CONTAINER} bash -c "cd /pipeline/source && PHANTOMJS_BIN=node_modules/.bin/phantomjs  npm run-script test"
}

function use_wercker {
    wercker build --direct-mount --pipeline static-validation &&
        wercker build --direct-mount --pipeline tests
}


if [ -z "${RUNNING_CONTAINER}" ]; then
    use_wercker
else
    use_running_container
fi

#if [ -n "$FILES" ] || [ -n "$FILES_CACHED" ] ; then
#    wercker build --direct-mount --pipeline static-validation &&
#        wercker build --direct-mount --pipeline tests
#else
#    echo "======================="
#    echo "======= No .py FILES TO COMMIT. SKIPING STATIC VALIDATION. "
#    echo "======================="
#    wercker build --direct-mount --pipeline tests
#fi


