import telebot
from telebot import types
import subprocess
import time
import mss
import mss.tools
import os
import threading
import random
from dotenv import load_dotenv

load_dotenv(dotenv_path="./.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# The window title keyword for wmctrl
EMULATOR_TITLE = "Android Emulator"

OFFSET_X = 10
OFFSET_Y = 40
CROP_WIDTH = 20
CROP_HEIGHT = 50
# ---------------------


def keep_app_awake():
    human_like_keep_alive()


def human_like_keep_alive():
    while True:
        time.sleep(random.uniform(30.0, 120.0))

        base_x, base_y = 500, 1000
        jitter_x = base_x + random.randint(-50, 50)
        jitter_y = base_y + random.randint(-50, 50)

        duration = random.randint(200, 600)

        cmd = f"adb shell input swipe {jitter_x} {jitter_y} {jitter_x + random.randint(-10, 10)} {jitter_y - random.randint(20, 80)} {duration}"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_window_geometry(title_keyword):
    """Finds the window, but prints what it finds for debugging."""
    try:
        output = subprocess.check_output(["wmctrl", "-l"]).decode("utf-8")
        print(f"DEBUG: wmctrl found the following windows:\n{output}")

        for line in output.splitlines():
            if title_keyword.lower() in line.lower():
                full_line = subprocess.check_output(["wmctrl", "-lG"]).decode("utf-8")
                for l in full_line.splitlines():
                    if line.split()[0] in l:
                        parts = l.split(None, 7)
                        return {
                            "id": parts[0],
                            "left": int(parts[2]),
                            "top": int(parts[3]),
                            "width": int(parts[4]),
                            "height": int(parts[5]),
                        }
    except Exception as e:
        print(f"Error reading window geometry: {e}")
    return None


@bot.message_handler(commands=["start"])
def send_welcome(message):
    """Sends the welcome message and displays the custom keyboard."""
    chat_id = message.chat.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_login = types.KeyboardButton("🔑 Auto Login")
    btn_screenshot = types.KeyboardButton("📸 Take Screenshot")
    markup.add(btn_login, btn_screenshot)

    bot.send_message(
        chat_id,
        "Welcome to the Automation Controller!\nUse the buttons below to interact with the emulator.",
        reply_markup=markup,
    )


@bot.message_handler(commands=["login"])
@bot.message_handler(func=lambda message: message.text == "🔑 Auto Login")
def handle_login_command(message):
    """Executes ADB touches to log into the app."""
    chat_id = message.chat.id
    bot.send_message(chat_id, "Initiating automated login sequence...")

    try:
        # REPLACE THESE COORDINATES WITH YOUR ACTUAL APP COORDINATES
        subprocess.run(["adb", "shell", "input", "tap", "250", "400"])  # Username field
        time.sleep(0.5)

        subprocess.run(["adb", "shell", "input", "text", "YOUR_USERNAME"])
        time.sleep(1)

        subprocess.run(["adb", "shell", "input", "tap", "250", "500"])  # Password field
        time.sleep(0.5)

        subprocess.run(["adb", "shell", "input", "text", "YOUR_PASSWORD"])
        time.sleep(1)

        subprocess.run(["adb", "shell", "input", "tap", "250", "650"])  # Login button

        bot.send_message(chat_id, "Login sequence executed.")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to execute ADB commands: {e}")


@bot.message_handler(commands=["screenshot"])
@bot.message_handler(func=lambda message: message.text == "📸 Take Screenshot")
def handle_screenshot_command(message):
    """Raises the window to the front and captures the screen securely."""
    chat_id = message.chat.id
    bot.send_message(chat_id, "Locating emulator and capturing screen...")

    monitor = get_window_geometry(EMULATOR_TITLE)

    if not monitor:
        bot.send_message(chat_id, "Error: Could not find the emulator window. Is it open?")
        return

    try:
        subprocess.run(["wmctrl", "-ia", monitor["id"]])
        time.sleep(0.5)
    except Exception as e:
        print(f"Could not bring window to front: {e}")

    safe_left = max(0, monitor["left"] - OFFSET_X)
    safe_top = max(0, monitor["top"] - OFFSET_Y)
    safe_width = max(100, monitor["width"])
    safe_height = max(100, monitor["height"])

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
        bot.send_message(chat_id, f"An error occurred during capture: {e}")


if __name__ == "__main__":
    awake_thread = threading.Thread(target=keep_app_awake, daemon=True)
    awake_thread.start()

    print("Bot is listening. Send /start in your Telegram chat to see the buttons.")
    bot.infinity_polling()
