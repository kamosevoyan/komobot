import json
import logging
import os
import queue
import random
import subprocess
import threading
import time

import cv2
import mss
import mss.tools
import telebot
from dotenv import load_dotenv
from PIL import Image
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

load_dotenv(dotenv_path="./.env")

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_PIN = os.getenv("APP_PIN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

DEEP_SLEEP_TIME = 3600
SOFT_SLEEP_TIME = 300

bot = telebot.TeleBot(BOT_TOKEN)

EMULATOR_TITLE = "Android Emulator"
APP_NAME = "ru.deltapay.puntopago.telcell"

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

# --- ACCESS CONTROL & CONCURRENCY ---
USERS_FILE = "/root/.android/allowed_users.json"
allowed_users = set()

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        allowed_users = set(json.load(f))


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(list(allowed_users), f)
        logger.info(f"User list updated and saved to {USERS_FILE}")


state = {"public_access_enabled": True}

emulator_lock = threading.Lock()
request_queue = queue.Queue()

# --- SLEEP STATE MANAGEMENT ---
emulator_is_sleeping = False


def wake_emulator_if_needed(chat_id=None):
    global emulator_is_sleeping
    if emulator_is_sleeping:
        if chat_id:
            bot.send_message(chat_id, "🥱 Waking up the emulator from deep sleep. This will take ~15 seconds...")
        logger.info("Waking up emulator from deep sleep...")

        # Launch the emulator process in the background
        subprocess.Popen(
            [
                "emulator",
                "-avd",
                "Pixel_Automation",
                "-memory",
                "2048",
                "-no-audio",
                "-gpu",
                "swiftshader_indirect",
                "-snapshot",
                "telcell_ready",
                "-no-snapshot-save",
                "-dns-server",
                "8.8.8.8,8.8.4.4",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Block until the ADB daemon is responsive again
        subprocess.run(["adb", "wait-for-device"], check=True)
        time.sleep(15)  # Allow the snapshot to fully load into memory

        # Reset any stale ADB connections
        subprocess.run(["adb", "kill-server"])
        subprocess.run(["adb", "start-server"])

        emulator_is_sleeping = False
        logger.info("Emulator is fully awake.")


# --- INACTIVITY TRACKING ---
last_interaction_time = time.time()


def update_activity():
    """Call this only inside user command handlers."""
    global last_interaction_time
    last_interaction_time = time.time()


def inactivity_monitor():
    logger.info("Inactivity monitor initialized.")
    while True:
        time.sleep(60)
        global last_interaction_time, emulator_is_sleeping

        inactive_time = time.time() - last_interaction_time

        # 1. Deep Sleep at 1 hour (3600 seconds)
        if inactive_time > DEEP_SLEEP_TIME and not emulator_is_sleeping:
            logger.info("Deep sleep threshold reached (1h). Shutting down emulator to free RAM...")
            with emulator_lock:
                # The 'emu kill' command safely powers down the QEMU virtual machine
                execute_adb(["emu", "kill"])
                emulator_is_sleeping = True

        # 2. Soft Lock at 5 minutes (300 seconds)
        elif (
            inactive_time > SOFT_SLEEP_TIME and inactive_time < int(1.2 * SOFT_SLEEP_TIME) and not emulator_is_sleeping
        ):
            logger.info("Inactivity limit reached (5m). Hard locking device...")
            with emulator_lock:
                execute_adb(["shell", "am", "force-stop", APP_NAME])
                execute_adb(["shell", "input", "keyevent", "3"])
                execute_adb(["shell", "input", "keyevent", "26"])
                logger.info("Inactivity lock sequence executed.")


def is_admin(message):
    return message.chat.id == ADMIN_ID


def is_allowed(message):
    return message.chat.id in allowed_users or message.chat.id == ADMIN_ID


# --- CORE SYSTEM FUNCTIONS ---
def execute_adb(args, delay=0.5, silent=False):
    cmd = ["adb"] + args
    cmd_str = " ".join(cmd)
    if not silent:
        logger.debug(f"Executing: {cmd_str}")
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
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


def keep_app_awake():
    logger.info("Hardware key keep-alive initialized.")
    while True:
        if not emulator_is_sleeping:
            try:
                execute_adb(["shell", "input", "keyevent", "24"], delay=0.5, silent=True)
                execute_adb(["shell", "input", "keyevent", "25"], delay=0.0, silent=True)
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")

        time.sleep(random.uniform(20.0, 45.0))


def get_window_geometry(title_keyword):
    try:
        output = subprocess.check_output(["wmctrl", "-lG"]).decode("utf-8")
        for line in output.splitlines():
            if title_keyword in line:
                parts = line.split(None, 7)
                if len(parts) >= 8:
                    w, h = int(parts[4]), int(parts[5])
                    if 100 < w < 1200 and h > 100:
                        return {"id": parts[0], "left": int(parts[2]), "top": int(parts[3]), "width": w, "height": h}
    except Exception as e:
        logger.error(f"Error reading window geometry: {e}")
    return None


def capture_debug_screenshot():
    """Captures the full emulator window for admin troubleshooting."""
    logger.info("Capturing full emulator window for debugging.")
    monitor = get_window_geometry(EMULATOR_TITLE)
    if not monitor:
        return None

    screenshot_path = "debug_screenshot.png"
    with mss.MSS() as sct:
        # Capture the raw window directly
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)

    return screenshot_path


def capture_qr_screenshot():
    """Captures, detects, and extracts only the QR code."""
    logger.info("Initiating QR detection and extraction.")
    monitor = get_window_geometry(EMULATOR_TITLE)
    if not monitor:
        return None

    screenshot_path = "qr_screenshot.png"
    try:
        # 1. Capture full window
        with mss.MSS() as sct:
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)

        # 2. Use OpenCV for QR Detection
        img = cv2.imread(screenshot_path)
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(img)

        if bbox is not None:
            # Calculate coordinates with padding
            pts = bbox[0].astype(int)
            x_min = max(0, min(pts[:, 0]) - 20)
            y_min = max(0, min(pts[:, 1]) - 20)
            x_max = min(img.shape[1], max(pts[:, 0]) + 20)
            y_max = min(img.shape[0], max(pts[:, 1]) + 20)

            # 3. Crop and overwrite
            cropped_img = img[y_min:y_max, x_min:x_max]
            cv2.imwrite(screenshot_path, cropped_img)
            return screenshot_path

        logger.warning("No QR code detected.")
        return None
    except Exception as e:
        logger.exception("Failed to extract QR code.")
        return None


def check_app_state():
    """
    Returns:
    'closed' - App not running
    'minimized' - App running but in the background
    'locked' - App open but PIN screen detected
    'ready'  - App open and dashboard detected
    'qr_section' - App in the QR section
    """
    # 1. Fast check for foreground activity
    res = subprocess.run(["adb", "shell", "dumpsys", "activity", "activities"], capture_output=True, text=True)
    if APP_NAME not in res.stdout:
        return "closed"

    is_foreground = False
    for line in res.stdout.splitlines():
        if ("mResumedActivity" in line or "topResumedActivity" in line) and APP_NAME in line:
            is_foreground = True
            break

    if not is_foreground:
        return "minimized"

    # 2. Check UI hierarchy directly from stdout (Zero host disk I/O, Zero artificial delay)
    # This command dumps the UI and prints it directly back to Python in milliseconds.
    ui_res = subprocess.run(
        ["adb", "shell", "uiautomator dump /sdcard/view.xml >/dev/null 2>&1 && cat /sdcard/view.xml"],
        capture_output=True,
        text=True,
    )

    content = ui_res.stdout

    if "Please enter PIN code" in content:
        return "locked"
    if "Buy tickets" in content:
        return "qr_section"

    return "ready"


def process_automated_screenshot(chat_id):
    bot.send_message(chat_id, "🔍 Checking app status...")

    with emulator_lock:
        # WAKE UP CHECK MUST HAPPEN FIRST
        wake_emulator_if_needed(chat_id)

        # Wake up device (1.0s is safe to ensure the screen powers on)
        execute_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=1.0)
        state = check_app_state()

        if state == "minimized":
            bot.send_message(chat_id, "🔄 App in background. Restoring...")
            # Reduced from 3.0s to 1.5s; restoring an app from RAM is very fast
            execute_adb(["shell", "monkey", "-p", APP_NAME, "1"], delay=1.5)
            state = check_app_state()

        elif state == "closed":
            bot.send_message(chat_id, "🚀 Launching app...")
            # Reduced from 4.0s to 3.0s; a warm emulator generally boots apps quickly
            execute_adb(["shell", "monkey", "-p", APP_NAME, "1"], delay=3.0)
            state = "locked"

        if state == "locked":
            bot.send_message(chat_id, "🔐 App locked. Entering PIN...")
            for digit in str(APP_PIN):
                if digit in PIN_COORDS:
                    # Reduced tap delay from 0.3s to 0.2s for faster PIN entry
                    execute_adb(["shell", "input", "tap", PIN_COORDS[digit][0], PIN_COORDS[digit][1]], delay=0.2)

            # Reduced dashboard load time from 2.0s to 1.5s
            time.sleep(1.5)
            state = "ready"

        if state == "ready":
            bot.send_message(chat_id, "📲 Generating QR...")
            # Reduced UI transition delays from 1.5s to 1.0s per tap
            execute_adb(["shell", "input", "tap", "40", "600"], delay=1.0)
            execute_adb(["shell", "input", "tap", "272", "172"], delay=1.0)
            state = "qr_section"

        if state == "qr_section":
            bot.send_message(chat_id, "📸 Capturing...")
            img_path = capture_qr_screenshot()

            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as photo:
                    bot.send_photo(chat_id, photo)
                os.remove(img_path)
            else:
                bot.send_message(chat_id, "❌ Capture error.")


def queue_worker():
    logger.info("Task queue worker initialized.")
    while True:
        chat_id = request_queue.get()
        logger.info(f"Dequeued request for user {chat_id}. Processing...")
        try:
            if not state["public_access_enabled"]:
                logger.info(f"Blocked request for user {chat_id} due to paused public access.")
                bot.send_message(chat_id, "⚠️ The admin has currently paused bot access. Try again later.")
            else:
                process_automated_screenshot(chat_id)
        except Exception as e:
            logger.exception(f"Queue worker failed while processing user {chat_id}.")
            bot.send_message(chat_id, "❌ An internal error occurred processing your request.")
        finally:
            request_queue.task_done()
            logger.info(f"Finished handling request for user {chat_id}.")


# --- BOT COMMANDS & HANDLERS ---
@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    logger.info(f"Received /start command from user: {chat_id}")
    if is_admin(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("📱 Open the app"),
            types.KeyboardButton("❌️ Close the app"),
            types.KeyboardButton("🔓 Unlock"),
            types.KeyboardButton("📲 Open QR"),
            types.KeyboardButton("📸 Take Screenshot"),
            types.KeyboardButton("🛑 Toggle Public Access"),
        )
        bot.send_message(
            chat_id,
            "👑 Admin Dashboard\nUse /adduser <id>, /listusers or /removeuser <id> to manage access.",
            reply_markup=markup,
        )
    elif is_allowed(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📸 Get Screenshot"))
        bot.send_message(chat_id, "Welcome! Press the button below to generate a QR code.", reply_markup=markup)
    else:
        logger.warning(f"Unauthorized access attempt by user: {chat_id}")
        bot.send_message(chat_id, "⛔ Unauthorized.")


# Admin User Management Commands
@bot.message_handler(commands=["adduser"], func=is_admin)
def add_user(message):
    try:
        new_id = int(message.text.split()[1])
        allowed_users.add(new_id)
        save_users()
        logger.info(f"Admin added new user: {new_id}")
        bot.reply_to(message, f"✅ User {new_id} added.")
    except Exception as e:
        logger.error(f"Failed to add user: {e}")
        bot.reply_to(message, "⚠️ Usage: /adduser <telegram_id>")


@bot.message_handler(commands=["listusers"], func=is_admin)
def list_users(message):
    logger.info("Admin requested user list.")
    if not allowed_users:
        bot.reply_to(message, "👥 The allowed users list is currently empty.")
        return
    user_list = "\n".join([f"• {uid}" for uid in allowed_users])
    bot.reply_to(message, f"👥 Allowed Users ({len(allowed_users)}):\n\n{user_list}")


@bot.message_handler(commands=["removeuser"], func=is_admin)
def remove_user(message):
    try:
        rem_id = int(message.text.split()[1])
        allowed_users.discard(rem_id)
        save_users()
        logger.info(f"Admin removed user: {rem_id}")
        bot.reply_to(message, f"🗑️ User {rem_id} removed.")
    except Exception as e:
        logger.error(f"Failed to remove user: {e}")
        bot.reply_to(message, "⚠️ Usage: /removeuser <telegram_id>")


@bot.message_handler(func=lambda m: m.text == "🛑 Toggle Public Access" and is_admin(m))
def toggle_access(message):
    state["public_access_enabled"] = not state["public_access_enabled"]
    status = "🟢 ENABLED" if state["public_access_enabled"] else "🔴 DISABLED"
    logger.info(f"Admin toggled public access: {status}")
    bot.reply_to(message, f"Public access is now {status}.")


# Regular User Flow
@bot.message_handler(func=lambda m: m.text == "📸 Get Screenshot" and is_allowed(m))
def handle_user_screenshot(message):

    update_activity()

    chat_id = message.chat.id
    logger.info(f"User {chat_id} requested an automated screenshot.")
    if not state["public_access_enabled"]:
        logger.info(f"Request from {chat_id} denied; access is disabled.")
        bot.reply_to(message, "⚠️ The bot is currently locked by the admin.")
        return
    bot.reply_to(message, "⏳ Added to the processing queue. Please wait...")
    request_queue.put(chat_id)


# Admin Raw Controls
@bot.message_handler(func=lambda m: m.text == "❌️ Close the app" and is_admin(m))
def handle_close_app(message):
    with emulator_lock:
        update_activity()

        chat_id = message.chat.id
        wake_emulator_if_needed(chat_id)

        logger.info("Admin requested to close the app.")
        bot.send_message(message.chat.id, "🧹 Closing the app...")
        if execute_adb(["shell", "am", "force-stop", APP_NAME], delay=1.0):
            logger.info("App successfully closed.")
            bot.send_message(message.chat.id, "✅ App closed successfully.")
        else:
            logger.error("Failed to close the app.")
            bot.send_message(message.chat.id, "❌ Failed to close the app.")


@bot.message_handler(func=lambda m: m.text == "📱 Open the app" and is_admin(m))
def handle_open_app(message):
    with emulator_lock:
        update_activity()

        chat_id = message.chat.id
        wake_emulator_if_needed(chat_id)

        logger.info("Admin requested to open the app.")
        bot.send_message(message.chat.id, "🚀 Opening the app...")
        if execute_adb(["shell", "monkey", "-p", APP_NAME, "1"], delay=2.0):
            logger.info("App successfully launched.")
            bot.send_message(message.chat.id, "✅ App opened successfully.")
        else:
            logger.error("Failed to open the app.")
            bot.send_message(message.chat.id, "❌ Failed to open the app.")


@bot.message_handler(func=lambda m: m.text == "🔓 Unlock" and is_admin(m))
def handle_unlock(message):
    with emulator_lock:
        update_activity()

        chat_id = message.chat.id
        wake_emulator_if_needed(chat_id)

        logger.info("Admin requested to unlock the app.")
        bot.send_message(message.chat.id, "🔐 Unlocking...")

        success = execute_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5)
        for digit in str(APP_PIN):
            if digit in PIN_COORDS:
                if not execute_adb(["shell", "input", "tap", PIN_COORDS[digit][0], PIN_COORDS[digit][1]], delay=0.3):
                    success = False

        if success:
            logger.info("PIN sequence executed successfully.")
            bot.send_message(message.chat.id, "✅ App unlocked successfully.")
        else:
            logger.error("Failed to execute PIN sequence.")
            bot.send_message(message.chat.id, "❌ Failed to unlock the app.")


@bot.message_handler(func=lambda m: m.text == "📲 Open QR" and is_admin(m))
def handle_just_qr(message):
    with emulator_lock:
        update_activity()

        chat_id = message.chat.id
        wake_emulator_if_needed(chat_id)

        logger.info("Admin requested to navigate to QR code.")
        bot.send_message(message.chat.id, "🧭 Navigating directly to QR code...")

        step1 = execute_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5)
        step2 = execute_adb(["shell", "input", "tap", "272", "172"], delay=1.5)

        if step1 and step2:
            logger.info("Navigated to QR code successfully.")
            bot.send_message(message.chat.id, "✅ QR Code opened successfully.")
        else:
            logger.error("Failed to navigate to QR screen.")
            bot.send_message(message.chat.id, "❌ Failed to open QR code.")


@bot.message_handler(func=lambda m: m.text == "📸 Take Screenshot" and is_admin(m))
def handle_screenshot_command(message):
    with emulator_lock:
        update_activity()

        chat_id = message.chat.id
        wake_emulator_if_needed(chat_id)

        logger.info("Admin requested a manual screenshot.")
        bot.send_message(message.chat.id, "🔍 Capturing screen...")
        img_path = capture_debug_screenshot()

        if img_path and os.path.exists(img_path):
            with open(img_path, "rb") as photo:
                bot.send_photo(message.chat.id, photo)
            os.remove(img_path)
            logger.info("Manual screenshot delivered to admin.")
            bot.send_message(message.chat.id, "✅ Screenshot captured successfully.")
        else:
            logger.error("Manual screenshot capture failed.")
            bot.send_message(message.chat.id, "❌ Capture error. Check logs for details.")


if __name__ == "__main__":
    awake_thread = threading.Thread(target=keep_app_awake, daemon=True)
    awake_thread.start()

    activity_thread = threading.Thread(target=inactivity_monitor, daemon=True)
    activity_thread.start()

    worker_thread = threading.Thread(target=queue_worker, daemon=True)
    worker_thread.start()

    logger.info("Bot is starting up and polling Telegram...")
    bot.infinity_polling()
