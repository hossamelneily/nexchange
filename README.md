# SETUP #

1. Optionally change POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in the services section of wercker.yml file

2. Optionally change values for other variables in the ENVIRONMENT file

3. run `$ werker dev --publish 8000` to start container

4. Access http://localhost:8000

#### ALL DONE ####

# Tests

**Every time  you do `git commit` the script.pre-commit.sh will run**.
It will trigger static validation of the code, running [flake8](https://flake8.readthedocs.io/en/latest/) followed by backenda nd frontend tests. (You can read more about the tests in the *readme_werker.md* on this directory.) 
**If any of this steps fail, file won't be commited.**

* To manually run the tests, do `wercker build --direct-mount --pipeline tests`

* To  manually run static validation (flake8) of the files you have changed, do `wercker build --direct-mount --pipeline static-validation`


