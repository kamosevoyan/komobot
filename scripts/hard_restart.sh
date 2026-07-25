#!/bin/bash

docker rm -f infernal-suffering
docker volume rm gehenna
docker volume create gehenna
docker build -t codex-gigas .
docker run -d \
    --env-file .env \
    -e BOOT_MODE=cold \
    --name infernal-suffering \
    --device /dev/kvm \
    --memory="3g" \
    --cpus="2" \
    -p 127.0.0.1:5900:5900 \
    -v gehenna:/root/.android \
    -v ./gomorrah:/app/sodom \
    codex-gigas
