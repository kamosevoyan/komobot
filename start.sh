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
    # Notice the new -dns-server flag added to the end
    emulator -avd Pixel_Automation -no-audio -gpu swiftshader_indirect -no-snapshot-load -dns-server 8.8.8.8,8.8.4.4 &
    
    echo "Waiting for Android OS to boot (this takes a few minutes)..."
    adb wait-for-device
    while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
        sleep 2
    done
    echo "Android is fully booted! Connect via VNC to do your manual setup."
    sleep 10

else
    echo "🚀 RESUME START MODE INITIATED..."
    # Notice the new -dns-server flag added to the end here too
    emulator -avd Pixel_Automation -no-audio -gpu swiftshader_indirect -snapshot telcell_ready -no-snapshot-save -dns-server 8.8.8.8,8.8.4.4 &
    
    echo "Waiting 15 seconds for Snapshot to resume..."
    sleep 15
fi
# -----------------------

echo "Starting Telegram Bot..."
python3 main.py
