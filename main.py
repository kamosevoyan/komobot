import telebot
from telebot import types
import subprocess
import time
import mss
import mss.tools
import os
import threading
import random
import logging
from dotenv import load_dotenv

# --- LOGGING SETUP ---
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(threadName)-12s | %(message)s",
    handlers=[logging.FileHandler(f"{LOG_DIR}/bot_activity.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
# ---------------------

load_dotenv(dotenv_path="./.env")

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_PIN = os.getenv("APP_PIN")
bot = telebot.TeleBot(BOT_TOKEN)

EMULATOR_TITLE = "Android Emulator"

OFFSET_X = 10
OFFSET_Y = 40
CROP_WIDTH = 20
CROP_HEIGHT = 50
# ---------------------


def keep_app_awake():
    logger.info("Hardware key keep-alive initialized.")
    while True:
        try:
            # 20 to 45 seconds is safe for most financial apps
            sleep_time = random.uniform(20.0, 45.0)
            time.sleep(sleep_time)

            logger.debug("Sending hardware volume key to keep session alive without touching UI.")
            # Volume Up (24)
            subprocess.run(
                ["adb", "shell", "input", "keyevent", "24"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            # Volume Down (25)
            subprocess.run(
                ["adb", "shell", "input", "keyevent", "25"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        except Exception as e:
            logger.exception("Keep-alive error!")
            time.sleep(5)


def get_window_geometry(title_keyword):
    """Finds the window managed by Fluxbox on X11."""
    try:
        output = subprocess.check_output(["wmctrl", "-lG"]).decode("utf-8")
        for line in output.splitlines():
            if title_keyword in line:
                parts = line.split(None, 7)
                if len(parts) >= 8:
                    w = int(parts[4])
                    h = int(parts[5])
                    if w > 100 and h > 100 and w < 1200:
                        return {
                            "id": parts[0],
                            "left": int(parts[2]),
                            "top": int(parts[3]),
                            "width": w,
                            "height": h,
                            "title": parts[7].strip(),
                        }
    except Exception as e:
        logger.error(f"Error reading window geometry: {e}")
    return None


@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    btn_unlock_qr = types.KeyboardButton("🔓 Unlock")
    btn_just_qr = types.KeyboardButton("📲 Open QR")
    btn_screenshot = types.KeyboardButton("📸 Take Screenshot")

    markup.add(btn_unlock_qr, btn_just_qr, btn_screenshot)
    bot.send_message(
        chat_id,
        "Welcome to the Automation Controller!\nChoose the action that matches the emulator's current state.",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda message: message.text == "🔓 Unlock")
def handle_unlock_qr(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Executing PIN unlock and navigating to QR code...")

    try:
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        time.sleep(0.5)

        if not APP_PIN:
            bot.send_message(chat_id, "Error: APP_PIN not found in .env file.")
            return

        subprocess.run(["adb", "shell", "input", "text", APP_PIN])
        logger.info("PIN entered via ADB.")
        time.sleep(4)  # Wait for dashboard

    except Exception as e:
        logger.exception("Failed to execute unlock macro.")
        bot.send_message(chat_id, f"An error occurred: {e}")


@bot.message_handler(func=lambda message: message.text == "📲 Open QR")
def handle_just_qr(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "App is already open. Navigating directly to QR...")
    try:
        subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        time.sleep(0.5)

        # Tap 1 (Replace X1, Y1)
        subprocess.run(["adb", "shell", "input", "tap", "272", "72"])
        time.sleep(1.5)

        # Tap 2 (Replace X2, Y2)
        subprocess.run(["adb", "shell", "input", "tap", "175", "175"])
        time.sleep(1)

        bot.send_message(chat_id, "✅ QR Code is ready! Press '📸 Take Screenshot'.")
    except Exception as e:
        logger.exception("Failed direct QR navigation.")
        bot.send_message(chat_id, f"Error: {e}")


@bot.message_handler(func=lambda message: message.text == "📸 Take Screenshot")
def handle_screenshot_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Locating emulator and capturing screen...")

    monitor = get_window_geometry(EMULATOR_TITLE)
    if not monitor:
        logger.warning("Screenshot requested, but wmctrl could not find window.")
        bot.send_message(chat_id, "Error: Could not find the emulator window.")
        return

    try:
        subprocess.run(["wmctrl", "-ia", monitor["id"]])
        time.sleep(0.5)
    except Exception as e:
        logger.error(f"Could not bring window to front: {e}")

    safe_left = max(0, monitor["left"] + OFFSET_X)
    safe_top = max(0, monitor["top"] + OFFSET_Y)
    safe_width = max(100, monitor["width"] - CROP_WIDTH)
    safe_height = max(100, monitor["height"] - CROP_HEIGHT)

    safe_monitor = {"left": safe_left, "top": safe_top, "width": safe_width, "height": safe_height}

    try:
        screenshot_path = "emu_screenshot.png"
        with mss.MSS() as sct:
            primary_monitor = sct.monitors[1]
            clamped_right = min(safe_monitor["left"] + safe_monitor["width"], primary_monitor["width"])
            clamped_bottom = min(safe_monitor["top"] + safe_monitor["height"], primary_monitor["height"])

            final_monitor = {
                "left": safe_monitor["left"],
                "top": safe_monitor["top"],
                "width": clamped_right - safe_monitor["left"],
                "height": clamped_bottom - safe_monitor["top"],
            }

            sct_img = sct.grab(final_monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)

        with open(screenshot_path, "rb") as photo:
            bot.send_photo(chat_id, photo)
        os.remove(screenshot_path)
    except Exception as e:
        logger.exception("Screenshot capture failed.")
        bot.send_message(chat_id, f"Capture error: {e}")


if __name__ == "__main__":
    awake_thread = threading.Thread(target=keep_app_awake, daemon=True)
    awake_thread.start()

    logger.info("Bot is starting up and polling Telegram...")
    bot.infinity_polling()
