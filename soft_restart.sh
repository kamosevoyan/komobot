#!/bin/bash

docker stop my-android-bot
docker rm my-android-bot
docker build -t android-bot-image .
docker run -d \
	--name my-android-bot \
	--device /dev/kvm \
	--privileged \
	-p 5900:5900 \
	-v emulator-data:/root/.android \
	-v ~/android_bot_logs:/app/logs \
	android-bot-image
