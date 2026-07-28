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

if [ "$BOOT_MODE" = "cold" ]; then
    echo "🧊 COLD START MODE INITIATED..."
    emulator -avd Pixel_Automation \
        -memory 2048 \
        -cores 2 \
        -no-audio \
        -gpu swiftshader_indirect \
        -no-snapshot-load \
        -dns-server 8.8.8.8,8.8.4.4 &

    echo "Waiting for Android OS to b oot..."
    adb wait-for-device
    while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
        sleep 2
    done
    echo "Android is fully booted!"
    sleep 10

else
    echo "🚀 RESUME START MODE INITIATED..."
    emulator -avd Pixel_Automation \
        -memory 2048 \
        -cores 2 \
        -no-audio \
        -gpu swiftshader_indirect \
        -no-snapshot-save \
        -dns-server 8.8.8.8,8.8.4.4 \
        -snapshot smart_snapshot \
        -no-boot-anim \
        -prop dalvik.vm.heapsize=256m \
        -prop qemu.sf.lcd_density=160 \
        -prop dalvik.vm.heaptargetutilization=0.9 &

    echo "Waiting 15 seconds for Snapshot to resume..."
    sleep 15
fi

echo "Disabling UI animations..."
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0

echo "Starting Telegram Bot..."
exec python3 main.py
