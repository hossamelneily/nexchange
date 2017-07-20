[![wercker status](https://app.wercker.com/status/067cf790e7047fabce4a0bdcd8d0cae8/s/ "wercker status")](https://app.wercker.com/project/byKey/067cf790e7047fabce4a0bdcd8d0cae8)
[![Code Coverage](https://scrutinizer-ci.com/g/onitsoft/nexchange/badges/coverage.png?b=release&s=09e925d0e3bb43ae9f0179ff1ccf6c42b0336fd1)](https://scrutinizer-ci.com/g/onitsoft/nexchange/?branch=release)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/onitsoft/nexchange/badges/quality-score.png?b=release&s=dea82d8c22adbb8b18ee327b9771fc5bbe08d335)](https://scrutinizer-ci.com/g/onitsoft/nexchange/?branch=release)
[![Build Status](https://scrutinizer-ci.com/g/onitsoft/nexchange/badges/build.png?b=release&s=0e65f940af2dbaadcbea7ee9a2e0ff2bac753da0)](https://scrutinizer-ci.com/g/onitsoft/nexchange/build-status/release)
# SETUP

1. Optionally change POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in the services section of wercker.yml file

2. Optionally change values for other variables in the ENVIRONMENT file

3. run `$ wercker dev --publish 8000` to start container

4. Access http://localhost:8000

# Tests
Tests always run when you commit, but you may want to run them mannualy sometimes. Therefore:

* To manually run the tests, do `wercker build --direct-mount --pipeline tests`
* To  manually run static validation (flake8) of the files you have changed, do `wercker build --direct-mount --pipeline static-validation`
* To manually run backend tests   `./run-tests.sh`
* To manually run backend tests and send coverage report to coveralls.io   `./run-tests.sh -c`
* To manually run Selenium UI  `./run-selenium-tests.sh`. Screenshots of the tests can be found in `nexchange/core/tests/test_ui/Screenshots`



# Commiting
**Every time  you do `git commit` the script.pre-commit.sh will run**.
It will trigger, in order: 
- static validation of the code, running [flake8](https://flake8.readthedocs.io/en/latest/) 
- backend tests (django unit tests)
- frontend tests (karma configures tests). 

**If any of this steps fail, file won't be commited.**

(After you run the tests, you can see a coverage report of the backend tests at http://localhost:8000/cover/index.html)

You can read more about these tests in the *readme_werker.md* on this directory.


# Development workflow#

- All features or anything which is not a one liner goes into a branch which results in a PR to `staging`.
 Which then must be reviewed, and propgated into a pull request.
- One liners and small patches can go to `staging`, with a PR to release.
- No commits, nor rebases on release
