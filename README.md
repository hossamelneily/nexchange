[![wercker status](https://app.wercker.com/status/067cf790e7047fabce4a0bdcd8d0cae8/s/ "wercker status")](https://app.wercker.com/project/byKey/067cf790e7047fabce4a0bdcd8d0cae8)
[![Coverage Status](https://coveralls.io/repos/github/onitsoft/nexchange/badge.svg?branch=HEAD&t=bsPMc2)](https://coveralls.io/github/onitsoft/nexchange?branch=HEAD)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/onitsoft/nexchange/badges/quality-score.png?b=release&s=dea82d8c22adbb8b18ee327b9771fc5bbe08d335)](https://scrutinizer-ci.com/g/onitsoft/nexchange/?branch=release)
[![Build Status](https://scrutinizer-ci.com/g/onitsoft/nexchange/badges/build.png?b=release&s=0e65f940af2dbaadcbea7ee9a2e0ff2bac753da0)](https://scrutinizer-ci.com/g/onitsoft/nexchange/build-status/release)

# DEPS

1. Docker
 - Ubuntu: follow this guide: https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/
 - MacOs: https://download.docker.com/mac/edge/Docker.dmg
 - Other dist: you should know what your doing
2. wercker-cli
 - Ubuntu: 
 ```
 curl -L https://s3.amazonaws.com/downloads.wercker.com/cli/stable/linux_amd64/wercker -o /usr/local/bin/wercker && chmod u+x /usr/local/bin/wercker
```
 - MacOS (home-brew required): 
 ```
  brew install wercker-cli && brew tap wercker/wercker
 ```
 Docs: https://www.wercker.com/wercker-cli
 https://www.wercker.com/cli/install/osx (OSX)
 https://www.wercker.com/cli/install/linux (Linux)

# SETUP

1. Optionally change POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in the services section of wercker.yml file

2. Optionally change values for other variables in the ENVIRONMENT file

3. run `$ wercker dev --expose-ports` to start container

4. Access http://localhost:8000

5. Disable Renos coin in case you are not running a local RPC node:
http://localhost:8000/en/admin/core/currency/33/change/
(tick disabled and save)
You will have to repeat this action for every time you start the `wercker-dev` pipeline until we implement a more permament solution.

# Tests
Tests always run when you commit, but you may want to run them mannualy sometimes. Therefore:

* To manually run the tests, do `wercker build --direct-mount --pipeline tests`
* To  manually run static validation (flake8) of the files you have changed, do `wercker build --direct-mount --pipeline static-validation`
* To manually run backend tests   `./run-tests.sh`
* To manually run backend tests and send coverage report to coveralls.io   `./run-tests.sh -c 1`
* To manually run exact backend test   `./run-tests.sh -t <test_case>` i.e.: ```./run-tests.sh -t nexchange.tests.test_tasks.test_e2e.ExchangeOrderReleaseTaskTestCase.test_release_exchange_order```
* To manually run exact backend test file(allows using TAB)   `./run-tests.sh -t <path_to_file>` i.e.: ```./run-tests.sh -t nexchange/tests/test_tasks/test_e2e.py```
* To manually run Selenium UI  `./run-selenium-tests.sh`. Screenshots of the tests can be found in `nexchange/core/tests/test_ui/Screenshots`
* To manually run API tests `./run-api-tests.sh`. More info [here](https://app.apiary.io/nexchange2/tests/runs#tutorial).


# Commiting
**Every time  you do `git commit` the script.pre-commit.sh will run**.
It will trigger, in order: 
- static validation of the code, running [flake8](https://flake8.readthedocs.io/en/latest/) 
- backend tests (django unit tests)

**If any of this steps fail, file won't be commited.**

(After you run the tests, you can see a coverage report of the backend tests at http://localhost:8000/cover/index.html)

You can read more about these tests in the *readme_werker.md* on this directory.


# Development workflow#

- All features or anything which is not a one liner goes into a branch which results in a PR to `staging`.
 Which then must be reviewed, and propgated into a pull request.
- One liners and small patches can go to `staging`, with a PR to release.
- No commits, nor rebases on release

# Running app with docker-compose
If you want to use pycharm debugger, you are going to have to run the app with docker-compose.

0. make a docker image of a running app. run `wercker dev --expose-ports` and then ` docker commit <running app container id>  onitsoft/runningapp`

1. You need to set up the remote interpreter. Go to project interpreter, choose  add remote, choose docker compose, set configuration file to `docker-compose-dev.yml`, service `app`, python path: `python`. If you set environment variables here to, it is possible, that the step 3 is not necessary, but I haven't tested it:

```
POSTGRES_USER=nexchange
POSTGRES_PASSWORD=nexchange
POSTGRES_DB=nexchange
POSTGIS_ENV_POSTGRES_DB=nexchange
POSTGIS_ENV_POSTGRES_USER=nexchange
POSTGIS_ENV_POSTGRES_PASSWORD=nexchange
```
2. In docker settings set /tmp folder to be mountable. Or remap folders in the `docker-compose-dev.yml` file to some mountable location.
3. Run it with `docker-compose -f docker-compose-dev.yml up` in the project directory. If there is no errors, you are lucky. If there are complaints, that database nexchange does not exist, or the role nexchange does not exist, or that user nexchange needs to be a super user, connect to the running db container `docker exec -it ce0fb4a6e4fd bash ` from your host machine, and run

```
su postgres
createdb nexchange
createuser -s nexchange
```
4. Again go to pycharm project interpreter settings. Set path mappings local path to local project folder on the host machine and remote path to `/pipeline/source`

5. In pycharm, set project build run script to `/pipeline/source/manage.py`, parameters to `runserver --settings=nexchange.settings_dev 0.0.0.0:8000` Interpreter should be set correctly to the remote interpreter by default.

Thats it, now you should be able to run the project and use the inbuilt debugger.

Set up [autopep8](https://github.com/hscgavin/autopep8-on-pycharm) and [isort](https://github.com/timothycrosley/isort/wiki/isort-Plugins). Use it on the files you edit. Set autopep8 `--max-line-length 79`