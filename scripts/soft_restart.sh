#!/bin/bash

docker stop infernal-suffering
docker rm infernal-suffering
docker build -t codex-gigas .
docker run -d \
    --env-file .env \
    -e BOOT_MODE=prod \
    --name infernal-suffering \
    --device /dev/kvm \
    --memory="3g" \
    --cpus="2" \
    -p 127.0.0.1:5900:5900 \
    -v gehenna:/root/.android \
    -v ./gomorrah:/app/sodom \
    codex-gigas
