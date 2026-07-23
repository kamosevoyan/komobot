# 🤖 Android Automation & FLAG_SECURE Bypass Bot

A highly robust, headless Android automation system encapsulated entirely within Docker. This project provides a Telegram Bot interface to control, navigate, and securely capture screenshots of high-security Android financial applications that enforce `FLAG_SECURE` (which normally blocks native Android screenshots).

## ✨ Key Features

* **FLAG_SECURE Bypass:** Instead of rooting the device or using `adb screencap` (which yields black screens for secure apps), this system runs Android inside a virtual X11 framebuffer (`Xvfb`) and uses `mss` and `wmctrl` to securely capture the host-level window buffer.

* **Snapshot State Teleportation:** Utilizes Android Emulator RAM snapshots to instantly resume the phone's state. This bypasses financial app "Cold Boot" security triggers and preserves SMS OTP authentication permanently.

* **Anti-Timeout & Anti-Fraud:** Bypasses aggressive idle-timeouts by simulating physical hardware volume key presses in the background, keeping the app awake without triggering heuristic touch-fraud sensors.

* **Custom In-App PIN Bypass:** Maps and executes touch events sequentially to bypass randomized or custom in-app PIN pads that block standard ADB keyboard input.

* **Fully Dockerized & Headless:** Runs completely invisibly in the background using nested KVM virtualization, a lightweight `fluxbox` window manager, and `x11vnc` for secure remote debugging.

## 🏗️ Architecture Stack

* **Host Requirement:** Ubuntu Linux with Hardware Virtualization (`/dev/kvm`) enabled. Cloud environments *must* support Nested Virtualization.
* **Container OS:** Ubuntu 22.04 LTS
* **Android OS:** x86_64 Android API 33 (Google APIs Playstore image for ARM-translation layer / libhoudini).
* **Display Server:** `Xvfb` (Virtual Framebuffer) + `fluxbox` (Window Manager).
* **Automation:** Python 3, `telebot` (Telegram), `mss` (Screenshot), `subprocess` (ADB).

## 🛠️ Prerequisites

1. A Linux machine (preferably Ubuntu) with an Intel/AMD CPU. Cloud servers *must* support Nested Virtualization (Bare Metal or specific instance types).
2. Hardware virtualization enabled:

```bash
   sudo apt install cpu-checker
   kvm-ok # Must output: "KVM acceleration can be used"
```

3. Docker installed and running.

## 🚀 Local Installation & Setup

### 1. Clone & Configure

Clone this repository and create a `.env` file in the root directory:

```text
BOT_TOKEN=your_telegram_bot_token_here
APP_PIN=1234
```

### 2. Calibrate Coordinates (Important!)

Before running the bot, you must calibrate the touch coordinates for your specific app using Android's **Pointer Location** developer tool.

* Open `main.py` and update the `PIN_COORDS` dictionary with the exact X/Y coordinates of your app's PIN pad.
* Update the `X` and `Y` tap coordinates in `main.py` to match your app's UI flow.

### 3. Build & Initialize Storage

```bash
docker build -t android-bot-image .
docker volume create emulator-data
mkdir ./android_bot_logs
```

## 🧊 The First Run (Cold Boot & Snapshot Setup)

Because financial apps require phone number verification and SMS OTPs, you must perform a manual "Cold Boot" setup once. It is highly recommended to do this on your **local machine** first.

**1. Start the container in Cold Mode locally:**

```bash
./scripts/run_cold.sh
```

**2. Connect via VNC:**

* Open a VNC Viewer and connect to `localhost:5900`.
* Log into the Google Play Store, download your target app, and log into the app completely.

**3. Save the RAM Snapshot:**

1. GUI version
   * In the VNC window, click the **Three Dots (...)** next to the emulator to open Extended Controls.
   * Navigate to **Snapshots**, and click **Take Snapshot**.
   * Name it exactly: `smart_snapshot`.
   * Close your VNC viewer and stop the container.
2. Shell version
   ```bash
   docker exec <container_name_or_id> adb emu avd snapshot save smart_snapshot
   ```

## ☁️ Cloud Deployment (Golden Volume Migration)

If you are deploying to a remote cloud server, setting up via VNC over the internet is slow and insecure. Instead, transfer your perfectly set up local volume to the cloud using the **Golden Volume** method.

**1. Compress the Local Volume:**
On your local machine, zip up the `emulator-data` volume containing your saved snapshot:

```bash
docker run --rm -v emulator-data:/volume -v $(pwd):/backup ubuntu tar cvzf /backup/emulator-backup.tar.gz -C /volume .
```

**2. Send to the Cloud:**
Securely copy the zipped file to your cloud server:

```bash
scp emulator-backup.tar.gz root@YOUR_CLOUD_IP:~/
```

**3. Unpack on the Cloud:**
SSH into your cloud server, build the Docker image, and unpack the data directly into the cloud's Docker volume:

```bash
docker volume create emulator-data
docker run --rm -v emulator-data:/volume -v $(pwd):/backup ubuntu bash -c "cd /volume && tar xvf /backup/emulator-backup.tar.gz"
```

## 🚀 Production Mode (Resume Boot)

Once your snapshot is saved locally (or unpacked on the cloud server), switch the bot to production mode. This will instantly teleport the emulator back to your logged-in state in milliseconds.

```bash
./scripts/run_resume.sh
```

Your bot is now running headlessly in the background! Open Telegram and use the custom keyboard to control the system.

## 📱 Telegram Bot Commands

The bot utilizes a custom Reply Keyboard with the following macros:

* **📱 Open the app:** Force-launches the application if it was closed.
* **❌️ Close the app:** Force-stops the application to clear the screen state.
* **🔓 Unlock:** Wakes the device, enters the custom 4-digit PIN via coordinate tapping, and prepares the dashboard.
* **📲 Open QR:** Navigates directly to the target QR code screen (assumes the app is already unlocked).
* **📸 Take Screenshot:** Uses `wmctrl` to focus the window and `mss` to capture a perfectly cropped, secure PNG of the internal framebuffer, bypassing Android UI security.

## 📂 Project Structure

* `main.py` - The core Python Telegram bot, logging setup, and ADB executor.
* `Dockerfile` - Builds the Ubuntu container with Xvfb, Fluxbox, Android SDK, and VNC.
* `start.sh` - The internal container entrypoint that manages X11 locks, dual-boot snapshot logic, and launches Python.
* `scripts/` - Host management scripts:
  * `run_resume.sh` - Host script to run the container in lightning-fast snapshot mode.
  * `run_cold.sh` - Host script to run the container in raw boot mode for manual maintenance.
  * `soft_restart.sh` - Host script to rebuild the image and safely restart without losing the Android data volume.
  * `hard_restart.sh` - **WARNING:** Wipes the Android data volume for a clean factory reset.