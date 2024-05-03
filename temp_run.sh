#!/bin/bash
set -ex
sudo docker run \
	-v $PWD:/FastSAM_ros/ \
	--ipc=host \
	--network="host" \
	--privileged=true \
	-v /etc/localtime:/etc/localtime:ro \
	-v /dev/video0:/dev/video0 --rm -it fastsam:services bash
