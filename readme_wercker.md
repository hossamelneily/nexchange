This file describes the wercker pipelines in this project and documents the configuration vars. All the pipelines are using the same image, which is `pitervergara/geodjango:nexchange`. This image is based on python:3.5 and adds geodjango required libs plus the python packages required by nexchange project at the time of the image creation. You can see the image details at https://hub.docker.com/r/pitervergara/geodjango/

# Dev #
run `$ werker dev --publish 8000` to start container
On dev pipeline, a docker container based on the public image is started and the app directory is mounted inside the container. The DJANGO_SETTINGS_MODULE is setted to **'nexchange.settings_dev'** and the variables from **ENVIRONMENT** file are exported by wercker. Then, the python requirements and the bower dependencies are installed, the migrations are created and applied. After all these steps, the django runserver command is executed, starting the server on port 8000.

# Build #
run `$ werker build` to check if the build will go OK when you push your code

Build pipelines looks like the 'dev' one. But after starting the container DJANGO_SETTINGS_MODULE is setted to **'nexchange.settings_prod'**. If the build is local the variables from  **ENVIRONMENT** file are exported, if the build is remote the variables defined in the web interface of wercker are exported.

During this pipeline, besides the steps executed in dev pipeline, the Django management commands **collectstatic** and **test** are also executed.

Close to the end, the *echo python information* step prints a few useful data about python and python package versions in this build

The last step (_copy files_) copies data to the  _$WERCKER_OUTPUT_DIR_, so the deploy pipeline has access to it.

As you see, the image is create but not publish in this pipeline. This is so that the _build_ step runs faster and developers can try it several times locally (passing through tests), before pushing to the remote repo.

# Deploy #
## The build, again ##
This is the pipeline which pushes the image to docker hub, from where it will be later pulled to be deployed.
This pipeline installs the requirements again (since the image from the previous pipeline was discarded). The bower dependencies are available in the copied files from build, so no need to install these again.
The pipeline *imports* the data copied to the  _$WERCKER_OUTPUT_DIR_ of the build pipeline. This data is copied to **/usr/src/app**.


An entrypoint script is created at **/entrypoint.sh**. This script cold have been created at build time, but generating it here allows that each deploy target define different values for the environment variables used in the initialization of the container.


Once all the file are im place, the **internal/docker-push** step publishes the image in docker hub. It sends the image to the $DOCKER_HUB_REPO repo, tagging it as $WERCKER_GIT_COMMIT (a hash produced and exported by wercker each time).
Note: This is a bad thing, because it depends that the target host has this script in that point.

## At the remote server ##
The last step is *Do deploy*, which connects to *$SSH_USER@$DEST_HOST_ADDR* and executes the steps to stop the current version of the container and start the new one.

After connecting on the remote server, the step logs in to dockerub (so the repo might be a private one) and pulls the ${DOCKER_HUB_REPO}:${WERCKER_GIT_COMMIT} image which was just pushed by the previous step.
Once the image is there, the local script (**./destroy-containers.sh**) is invoked to stop and remove containers that have the same name of the one that is being deployed (it will have the same name if you trigger a deploy from wercker interface multiple times) and any other that comes from the ${DOCKER_HUB_REPO} repo, wich will be problably match only the previous version of the container that we are deploying.

After the current version is stoped the new one is start with a link to **${DATABASE_CONTAINER},** some ports publish (according to ${PORTS_PARAM}) and some volumes mounted (according to ${VOLUMES_PARAM}). As soon as it starts the */entrypoint.sh* script will run.

### About the entrypoint script ###
The script exports a few variables, then runs the **migrate** management command to apply in the production database the new migrations created at build time (if any). Then the script copies the static and media files to the **/usr/share/nginx/html** which **is expected to be a volume from the host which is served by nginx**.

Note: One better solution would be to mount host directories directly into /usr/src/app/static and /usr/src/app/media, if we can assure that everything that is in those directories can be recreated with *collectstatic* and *bower install*.
Lastly the script starts a backgroud process to monitor the gunicorn logs (which allows `docker logs container` to show gunicorn logs) and start the gunicorn server at 0.0.0.0:${GUNICORN_PORT}.


### About the database ###
For dev and build pipelines a service with postgres+postgis is used. The life cycle and linking of this service container is totally managed by wercker.

In the current config, when the app is deployed to a target, is does not have the database server automatically created, therefore **is expected that a database container is up and running  when the app container starts**.

Currently, the database container is running an instance of [mdillon/postgis](https://hub.docker.com/r/mdillon/postgis/) image (the same one used in dev and build steps). This container was started with the folowing line:
`docker run --name nexchange-db -v /data/database:/var/lib/postgresql/data -e POSTGRES_PASSWORD=a071fd4b1aac00497d4c561e530b5738 -e POSTGRES_USER=nexchnage -e POSTGRES_DB=nexchange -d mdillon/postgis`

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