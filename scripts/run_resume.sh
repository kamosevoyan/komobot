#!/bin/bash

docker rm -f my-android-bot
docker run -d \
	--env-file .env \
	-e BOOT_MODE=prod \
	--name my-android-bot \
	--device /dev/kvm \
	--memory="3g" \
	--cpus="2" \
	-p 127.0.0.1:5900:5900 \
	-v emulator-data:/root/.android \
	-v ./android_bot_logs:/app/logs \
	android-bot-image
# --privileged \
