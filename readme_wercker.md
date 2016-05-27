This file describes the wercker pipelines in this project and documents the configuration vars. All the pipelines are using the same image, which is `pitervergara/geodjango:nexchange`. This image is based on python:3.5 and adds geodjango required libs plus the python packages required by nexchange project at the time of the image creation. You can see the image details at https://hub.docker.com/r/pitervergara/geodjango/

# Dev #
run `$ werker dev --publish 8000` to start container
On dev pipeline, a docker container based on the public image is started and the app directory is mounted inside the container. The DJANGO_SETTINGS_MODULE is setted to **'nexchange.settings_dev'** and the variables from **ENVIRONMENT** file are exported by wercker. Then, the python requirements and the bower dependencies are installed, the migrations are created and applied. After all these steps, the django runserver command is executed, starting the server on port 8000.

# Build #
run `$ werker build` to check if the build will go OK when you push your code

Build pipelines looks like the 'dev' one. But after starting the container DJANGO_SETTINGS_MODULE is setted to **'nexchange.settings_prod'**. If the build is local the variables from  **ENVIRONMENT** file are exported, if the build is remote the variables defined in the web interface of wercker are exported.

During this pipeline, besides the steps executed in dev pipeline, the Django management commands **collectstatic** and **test** are also executed.

Close to the end, the *echo python information* step prints a few useful data about python and python package versions in this build

The step (_copy files_) copies data into the contianer, to the places they should be for runnning on production. The static and media, will be later copied again to another place. This is done in a second step because the container should be already in execution and with the volumes mounted (which is not the case during the build).

The build pipeline also creates an entripoint script at **/entrypoint.sh**, inside the container. This is the script executed by the container as soon as it starts.

Once all the files are im place, the **internal/docker-push** step publishes the image in docker hub. It sends the image to the $DOCKER_HUB_REPO repo, tagging it as $WERCKER_GIT_COMMIT (a hash produced and exported by wercker each time).


# Deploy #
In this step the pipeline remotely logis into the production server ($DEST_HOST_ADDR) and replaces the running container with the version corresponding to the last $WERCKER_GIT_COMMIT.

Initialy, the pipeline creates a local file containing the private key used to login and copy the **remove-containers.sh** script to the destination server.

## At the remote server ##
The *Do deploy* step connects to *$SSH_USER@$DEST_HOST_ADDR* and executes the steps to stop the current version of the container and start the new one.

After connecting on the remote server, the step logs in to dockerub (so the repo might be a private one) and pulls the ${DOCKER_HUB_REPO}:${WERCKER_GIT_COMMIT} image which was pushed in the build pipeline.
Once the image is there, the copy of **remove-container.sh** script is invoked to stop and remove containers which the name starts with *nexchange_*.

After the current version is out the new one is started with a link to **${DATABASE_CONTAINER},** some ports publish (according to ${PORTS_PARAM}) and some volumes mounted (according to ${VOLUMES_PARAM}). As soon as it starts the */entrypoint.sh* script will run.

### About the entrypoint script ###
The script exports a few variables, then runs the **migrate** management command to apply in the production database the new migrations created at build time (if any). Then the script copies the static and media files to the **/usr/share/nginx/html** which **is expected to be a volume from the host which is served by nginx**.

Lastly the script starts a backgroud process to monitor the gunicorn logs (which allows `docker logs container` to show gunicorn logs) and start the gunicorn server at 0.0.0.0:${GUNICORN_PORT}.


### About the database ###
For dev and build pipelines a service with postgres+postgis is used. The life cycle and linking of this service container is totally managed by wercker.

In the current config, when the app is deployed to a target, is does not have the database server automatically created, therefore **is expected that a database container is up and running  when the app container starts**.

Currently, the database container is running an instance of [mdillon/postgis](https://hub.docker.com/r/mdillon/postgis/) image (the same one used in dev and build steps). At the production server this container was started with the folowing line:
`docker run --name nexchange-db -v /data/database:/var/lib/postgresql/data -e POSTGRES_PASSWORD=a071fd4b1aac00497d4c561e530b5738 -e POSTGRES_USER=nexchange -e POSTGRES_DB=nexchange -d mdillon/postgis`

----
# Enviroment variables #
## for dev ##

## for build and deploy ##
- `PEM_FILE_CONTENT` - The key to SSH into server (create key par via wercker web interface. remeber to install public key on target server)
- `SSH_USER` - the user to SSH into server
- `DEST_HOST_ADDR` - server where to deploy 
- `DATABASE_CONTAINER` - DB container to which the container will be linked
- `POSTGIS_ENV_POSTGRES_USER` - DB username used to connect to DATABASE_CONTAINER
- `POSTGIS_ENV_POSTGRES_PASSWORD` - the password for POSTGIS_ENV_POSTGRES_USER
- `POSTGIS_ENV_POSTGRES_DB` - the name of the database to connect to
- `GUNICORN_PORT` - the port in which gunicorn will run inside the container 
- `VOLUMES_PARAM` - a list o volumes (each preceded by -v to mount in container)
- `PORTS_PARAM` - a list of ports (preceded by -p) to expose from the container 
- `DOCKER_HUB_USER` - dockerhub username to push and pull container images
- `DOCKER_HUB_PASSWORD` - password for DOCKER_HUB_USER (define it as a protectd var)
- `DOCKER_HUB_REPO` - the dockerhub repo where to push (repo must already exists and could be  private)

----
# Other useful informations

The nginx which serves as Web server is not containerized, but installed directly in the host *nexchange.co.uk*. The configuration file is not managed by the pipeline, although a copy of the first (and hopefully the current) version is in this repo. The file is  **nginx.conf**.

The **ticker** component of nexchange is invoke by a cron job that runs at the host *nexchange.co.uk*. The cronjob **is not managed by the deploy**.
The original (and hopefully the current) entry of the **/etc/cronjob** that invokes the ticker is the following:

`* * * * * root docker exec $(docker ps -q -a --filter "name=nexchange_") python manage.py ticker`

This line identifies the id of the container and runs a *docker exec* into it, calling the django management command.


