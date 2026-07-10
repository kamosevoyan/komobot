#!/bin/bash

echo "Starting Virtual Display and Window Manager..."
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

fluxbox &
sleep 1

echo "Starting VNC Server on port 5900..."
x11vnc -display :99 -nopw -forever -bg -quiet

# --- DUAL BOOT LOGIC ---
if [ "$BOOT_MODE" = "cold" ]; then
	echo "🧊 COLD START MODE INITIATED..."
	# -no-snapshot-load forces a raw, normal Android boot
	emulator -avd Pixel_Automation -no-audio -gpu swiftshader_indirect -no-snapshot-load &

	echo "Waiting for Android OS to boot (this takes a few minutes)..."
	adb wait-for-device
	while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
		sleep 2
	done
	echo "Android is fully booted! Connect via VNC to do your manual setup."
	sleep 10

else
	echo "🚀 RESUME START MODE INITIATED..."
	# Instantly teleports to your saved RAM state
	emulator -avd Pixel_Automation -no-audio -gpu swiftshader_indirect -snapshot telcell_ready -no-snapshot-save &

	echo "Waiting 15 seconds for Snapshot to resume..."
	sleep 15
fi
# -----------------------

echo "Starting Telegram Bot..."
python3 main.py
