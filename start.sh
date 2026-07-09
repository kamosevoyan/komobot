#!/bin/bash

Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

sleep 5

emulator -avd Pixel_Automation -no-window -gpu swiftshader_indirect &

sleep 45

python3 main.py
