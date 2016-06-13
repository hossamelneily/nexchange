# SETUP #

1. Optionally change POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB in the services section of wercker.yml file

2. Optionally change values for other variables in the ENVIRONMENT file

3. run `$ werker dev --publish 8000` to start container

4. Access http://localhost:8000

# Tests # 

1. To run the tests, do `wercker build --pipeline tests --docker-local`

#### ALL DONE ####
