#!/bin/bash

RUNNING_CONTAINER=$(docker ps -q --filter name='^/nexchange_app|wercker-pipeline-' --filter status=running)

function use_running_container {
    coverage_cmd="coverage erase"
    coverage_cmd="${coverage_cmd} && coverage run --source='.' --omit='src/' manage.py test -v 3 --pattern='test_*.py'"
    coverage_cmd="${coverage_cmd} && coverage report "
    coverage_cmd="${coverage_cmd} && coverage html -d cover"
    api_tests_cmd="./manage.py test --failfast -v=3 --pattern='api_test*.py'"

    echo "${coverage_cmd}"

    static_validation_cmd_py="cd /pipeline/source && ./static-validation-py.sh"
    static_validation_cmd_js="cd /pipeline/source && ./static-validation-js.sh"
    backend_tests="cd /pipeline/source && export DJANGO_SETTINGS_MODULE=nexchange.settings_test && ${coverage_cmd}"
    api_tests="cd /pipeline/source && export DJANGO_SETTINGS_MODULE=nexchange.settings_test && ${api_tests_cmd}"
    frontend_tests="cd /pipeline/source && PHANTOMJS_BIN=node_modules/.bin/phantomjs  npm run-script test"

    docker exec -t ${RUNNING_CONTAINER} bash -c "${static_validation_cmd_py}" &&
        docker exec -t ${RUNNING_CONTAINER} bash -c "${static_validation_cmd_js}" &&
            docker exec -t ${RUNNING_CONTAINER} bash -c "${api_tests}"
}

function use_wercker {
    wercker build --direct-mount --pipeline static-validation-py &&
        wercker build --direct-mount --pipeline static-validation-js &&
            wercker build --direct-mount --pipeline tests
}

function use_docker_compose {
    docker-compose -f docker-compose-dev.yml up &&
    echo "started a new app container"
}

autopep8 --in-place --aggressive --aggressive `ls **/**/**.py | grep -v /migrations/`


if [ -z "${RUNNING_CONTAINER}" ]; then
    echo -e "\e[33mDid not found a running container for the nexchange project. Starting one to execute the pre-commit hook.\e[39m"
    use_docker_compose
fi

RUNNING_CONTAINER=$(docker ps -q --filter name='^/nexchange_app|wercker-pipeline-' --filter status=running)
if [ -z "${RUNNING_CONTAINER}" ]; then
    use_wercker
fi

RUNNING_CONTAINER=$(docker ps -q --filter name='^/nexchange_app|wercker-pipeline-' --filter status=running)
if [ -z "${RUNNING_CONTAINER}" ]; then
    echo -e "\e[32m Failed to find or start an app container to run precommit hooks. Manually check whats wrong.\e[39m"
    exit 1
else
    echo -e "\e[32mRunning pre-commit hook inside the container with id ${RUNNING_CONTAINER}, which is believed to be nexchange dev.\e[39m"
    use_running_container
fi
