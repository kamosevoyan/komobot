#!/bin/bash

echo "🧹 Cleaning up stale system locks..."
rm -rf /tmp/.X* /tmp/.X11-unix/*
adb kill-server
sleep 1

find /root/.android/avd/ -name "*.lock" -delete
sleep 1

echo "Starting Virtual Display and Window Manager..."
Xvfb :99 -screen 0 1280x1024x24 &
sleep 2

fluxbox &
sleep 1

if [ "$BOOT_MODE" != "prod" ]; then
	echo "Starting VNC Server on port 5900..."
	x11vnc -display :99 -nopw -forever -bg -quiet
fi

EMU_ARGS=($(<src/core/emu_args.txt))

if [ "$BOOT_MODE" = "cold" ]; then
	echo "🧊 COLD START MODE INITIATED..."
	emulator "${EMU_ARGS[@]}" -no-snapshot-load &

	echo "Waiting for Android OS to boot..."
	adb wait-for-device
	while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
		sleep 2
	done
	echo "Android is fully booted!"
	sleep 10

else
	echo "🚀 RESUME START MODE INITIATED..."
	emulator "${EMU_ARGS[@]}" -no-snapshot-save -snapshot smart_snapshot &

	echo "Waiting 15 seconds for Snapshot to resume..."
	sleep 15
fi

echo "Disabling UI animations..."
for animation_setting in window_animation_scale transition_animation_scale animator_duration_scale; do
	adb shell settings put global "$animation_setting" 0
done

echo "Disabling Apps..."
for app in com.android.chrome com.google.android.youtube com.google.android.gm com.google.android.apps.photos; do
	adb shell pm disable-user --user 0 "$app"
done

adb shell settings put global auto_time 0
adb shell settings put secure location_mode 0

echo "Starting Telegram Bot..."
exec python3 main.py
