# stop and remove existent containers          
sudo docker stop $(docker ps -q --filter "name=$1") 2>/dev/null
sudo docker rm $(docker ps -q -a --filter "name=$1") 2>/dev/null