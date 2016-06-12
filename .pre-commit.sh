#!/bin/sh
PROJECT_DIR=$(cd $(dirname "${BASH_SOURCE[0]}") && cd ../../ && pwd) 
cd "${PROJECT_DIR}"

CONTAINER_ID="$(docker ps --filter "ancestor=pitervergara/geodjango:nexchange" --filter "name=wercker-pipeline" --filter "status=running" -q)"
QTD_IDS=$(egrep -o "[0-9a-z]{12}" <<< "${CONTAINER_ID}" | wc -l)

if [ "${QTD_IDS}" == "1" ]; then
    echo "Assuming that container with ID ${CONTAINER_ID} is the one for nexchange"
    echo "Running tests into container ${CONTAINER_ID}"
    
    docker exec -i ${CONTAINER_ID} bash -c "cd /pipeline/source && bash static-validation.sh" &&
    docker exec -i ${CONTAINER_ID} bash -c "DJANGO_SETTINGS_MODULE=nexchange.settings_test cd /pipeline/source && python manage.py test -v 3" &&
    docker exec -i ${CONTAINER_ID} bash -c "export PHANTOMJS_BIN=/pipeline/source/node_modules/.bin/phantomjs && cd /pipeline/source && npm run-script test"
else
    echo "${QTD_IDS} containers found. Cannot determine the nexchange one."
    echo "Running wercker step for static-validation and tests."

    wercker build --direct-mount --pipeline static-validation && wercker build --direct-mount --pipeline tests    
fi



