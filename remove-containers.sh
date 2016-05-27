# stop and remove existent containers          
sudo docker stop $(sudo docker ps -q --filter "name=$1") 2>/dev/null
sudo docker rm $(sudo docker ps -q -a --filter "name=$1") 2>/dev/null