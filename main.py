import logging
import os
import random
import subprocess
import threading
import time

import mss
import mss.tools
import telebot
from dotenv import load_dotenv
from telebot import types

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
APP_NAME = "ru.deltapay.puntopago.telcell"

OFFSET_X = 10
OFFSET_Y = 40
CROP_WIDTH = 20
CROP_HEIGHT = 50

# --- PIN PAD COORDINATES ---
PIN_COORDS = {
    "1": ("77", "438"),
    "4": ("77", "476"),
    "7": ("77", "514"),
    "2": ("160", "438"),
    "5": ("160", "476"),
    "8": ("160", "514"),
    "0": ("160", "552"),
    "3": ("243", "438"),
    "6": ("243", "476"),
    "9": ("243", "514"),
}
# ---------------------


# --- CORE ADB EXECUTOR ---
def execute_adb(args, delay=0.5, silent=False):
    """
    Executes an ADB command safely, logs the output, and applies a mandatory delay.
    :param args: List of arguments after 'adb' (e.g. ["shell", "input", "tap", "X", "Y"])
    :param delay: Seconds to wait after execution to allow the UI to catch up.
    :param silent: If True, suppresses normal logs (useful for spammy keep-alive commands).
    :return: True if successful, False if the command failed.
    """
    cmd = ["adb"] + args
    cmd_str = " ".join(cmd)

    if not silent:
        logger.debug(f"Executing: {cmd_str}")

    try:
        # capture_output lets us read exactly why ADB failed if it crashes
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if delay > 0:
            time.sleep(delay)
        return True
    except subprocess.CalledProcessError as e:
        if not silent:
            logger.error(f"ADB command failed: {cmd_str} | Error: {e.stderr.strip()}")
        return False
    except Exception as e:
        if not silent:
            logger.exception(f"Unexpected error running ADB: {cmd_str}")
        return False


# -------------------------


def keep_app_awake():
    logger.info("Hardware key keep-alive initialized.")
    while True:
        try:
            sleep_time = random.uniform(20.0, 45.0)
            time.sleep(sleep_time)

            # Use the new helper function in silent mode so we don't flood the logs
            execute_adb(["shell", "input", "keyevent", "24"], delay=0.5, silent=True)  # Volume Up
            execute_adb(["shell", "input", "keyevent", "25"], delay=0.0, silent=True)  # Volume Down

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

    btn_unlock = types.KeyboardButton("🔓 Unlock")
    btn_open_qr = types.KeyboardButton("📲 Open QR")
    btn_screenshot = types.KeyboardButton("📸 Take Screenshot")
    btn_open_app = types.KeyboardButton("📱 Open the app")
    btn_close_app = types.KeyboardButton("❌️ Close the app")

    markup.add(btn_open_app, btn_close_app, btn_unlock, btn_open_qr, btn_screenshot)
    bot.send_message(
        chat_id,
        "Welcome to the Automation Controller! 🤖\nChoose an action below to interact with the emulator.",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda message: message.text == "❌️ Close the app")
def handle_close_app(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🧹 Closing the app...")

    if execute_adb(["shell", "am", "force-stop", APP_NAME], delay=1.0):
        logger.info("App closed successfully.")
    else:
        bot.send_message(chat_id, "⚠️ Failed to close the app. Check the logs.")


@bot.message_handler(func=lambda message: message.text == "📱 Open the app")
def handle_open_app(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🚀 Opening the app...")

    if execute_adb(["shell", "monkey", "-p", APP_NAME, "1"], delay=2.0):
        logger.info("App launched successfully.")
    else:
        bot.send_message(chat_id, "⚠️ Failed to open the app. Check the logs.")


@bot.message_handler(commands=["login"])
@bot.message_handler(func=lambda message: message.text == "🔓 Unlock")
def handle_login_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔐 Initiating automated PIN sequence...")

    execute_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5)

    if not APP_PIN:
        bot.send_message(chat_id, "❌ Error: APP_PIN not found in .env file.")
        logger.error("Unlock failed: Missing APP_PIN.")
        return

    logger.info("Executing PIN sequence...")
    success = True

    for digit in str(APP_PIN):
        if digit in PIN_COORDS:
            x, y = PIN_COORDS[digit]
            if not execute_adb(["shell", "input", "tap", x, y], delay=0.3):
                success = False
                break
        else:
            logger.warning(f"Digit '{digit}' not found in coordinate map. Skipping.")

    if success:
        bot.send_message(chat_id, "✅ PIN sequence executed successfully.")
    else:
        bot.send_message(chat_id, "⚠️ Something went wrong during the PIN sequence. Check logs.")


@bot.message_handler(func=lambda message: message.text == "📲 Open QR")
def handle_just_qr(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🧭 Navigating directly to QR code...")

    execute_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5)

    if execute_adb(["shell", "input", "tap", "272", "172"], delay=1.5):
        bot.send_message(chat_id, "✅ QR Code is ready! Press '📸 Take Screenshot'.")
    else:
        bot.send_message(chat_id, "⚠️ Failed to navigate to QR code.")


@bot.message_handler(func=lambda message: message.text == "📸 Take Screenshot")
def handle_screenshot_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔍 Locating emulator and capturing screen...")

    monitor = get_window_geometry(EMULATOR_TITLE)
    if not monitor:
        logger.warning("Screenshot requested, but wmctrl could not find window.")
        bot.send_message(chat_id, "❌ Error: Could not find the emulator window on the host.")
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
        logger.info("Screenshot successfully taken and sent to Telegram.")

    except Exception as e:
        logger.exception("Screenshot capture failed.")
        bot.send_message(chat_id, "❌ Capture error. Check the server logs for details.")


if __name__ == "__main__":
    awake_thread = threading.Thread(target=keep_app_awake, daemon=True)
    awake_thread.start()

    logger.info("Bot is starting up and polling Telegram...")
    bot.infinity_polling()
