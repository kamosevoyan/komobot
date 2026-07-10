#!/bin/bash

docker rm -f my-android-bot
docker run -d \
	--name my-android-bot \
	--device /dev/kvm \
	--privileged \
	-e BOOT_MODE=resume \
	-p 5900:5900 \
	-v emulator-data:/root/.android \
	-v ~/android_bot_logs:/app/logs \
	android-bot-image
