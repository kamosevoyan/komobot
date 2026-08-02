#!/bin/bash

CONTAINER_NAME="infernal-suffering"
IMAGE_NAME="codex-gigas"
VOLUME_NAME="gehenna"
ENV_FILE=".env"

show_help() {
	echo "Usage: ./manage.sh [COMMAND]"
	echo ""
	echo "Commands:"
	echo "  resume        (Default) Run the container in production mode [run_resume.sh logic]"
	echo "  cold          Run the container in cold boot mode [run_cold.sh logic]"
	echo "  soft-restart  Rebuild the Docker image and run in production mode [soft_restart.sh logic]"
	echo "  hard-restart  Wipe volumes, rebuild the image, and run in cold boot mode [hard_restart.sh logic]"
	echo "  help          Show this help message"
}

remove_container() {
	echo "🧹 Cleaning up existing container..."
	docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
}

build_image() {
	echo "🏗️ Building Docker image '$IMAGE_NAME'..."
	docker build -t "$IMAGE_NAME" .
}

run_container() {
	local boot_mode=$1
	echo "🚀 Starting container '$CONTAINER_NAME' with BOOT_MODE=$boot_mode..."
	docker run -d \
		--env-file "$ENV_FILE" \
		-e BOOT_MODE="$boot_mode" \
		--name "$CONTAINER_NAME" \
		--device /dev/kvm \
		--memory="3g" \
		--cpus="3" \
		-p 127.0.0.1:5900:5900 \
		-v "$VOLUME_NAME:/root/.android" \
		-v ./gomorrah:/app/sodom \
		"$IMAGE_NAME"
}

confirm_wipe() {
	echo "⚠️  This will PERMANENTLY DELETE the '$VOLUME_NAME' volume, including your"
	echo "    saved Android snapshot and logged-in app session."
	read -r -p "Type YES to confirm: " reply
	if [ "$reply" != "YES" ]; then
		echo "Aborted. Nothing was deleted."
		exit 1
	fi
}

case "$1" in
	"hard-restart")
		echo "🔥 INITIATING HARD RESTART"
		confirm_wipe
		remove_container
		echo "🗑️ Wiping Android data volume..."
		docker volume rm "$VOLUME_NAME" 2>/dev/null || true
		docker volume create "$VOLUME_NAME"
		build_image
		run_container "cold"
		;;
	"soft-restart")
		echo "🔄 INITIATING SOFT RESTART"
		remove_container
		build_image
		run_container "prod"
		;;
	"cold")
		echo "🧊 INITIATING COLD BOOT"
		remove_container
		run_container "cold"
		;;
	"resume" | "")
		echo "⚡ INITIATING RESUME BOOT"
		remove_container
		run_container "prod"
		;;
	"help" | *)
		show_help
		exit 1
		;;
esac
