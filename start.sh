#!/bin/bash

echo "Starting Virtual Display and Window Manager..."
# Start the virtual screen
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

# Start the window manager (REQUIRED for wmctrl and window coordinates)
fluxbox &
sleep 1

echo "Starting VNC Server on port 5900..."
# Allow remote viewing of the virtual display
x11vnc -display :99 -nopw -forever -bg -quiet

echo "Starting Android Emulator..."
# Boot the emulator inside Xvfb. 
# swiftshader_indirect forces CPU rendering since Docker has no GPU.
emulator -avd Pixel_Automation -no-audio -gpu swiftshader_indirect &

echo "Waiting for Android OS to boot (this may take a few minutes)..."
# Smart polling: Check ADB until the boot animation finishes
adb wait-for-device
while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
    sleep 2
done
echo "Android is fully booted!"

# Give the UI an extra 10 seconds to render the home screen
sleep 10

echo "Starting Telegram Bot..."
python3 main.py