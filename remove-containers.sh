# stop and remove existent containers          
docker stop $(docker ps -q --filter "name=$1") 2>/dev/null
docker rm $(docker ps -q -a --filter "name=$1") 2>/dev/null