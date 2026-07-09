#!/bin/bash

docker rm -f my-android-bot
docker volume rm emulator-data
docker volume create emulator-data
docker build -t android-bot-image .
docker run -d \
	--name my-android-bot \
	--device /dev/kvm \
	--privileged \
	-p 5900:5900 \
	-v emulator-data:/root/.android \
	android-bot-image
