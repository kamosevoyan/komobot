import json
import os
import queue
import threading

import telebot
from telebot import types


class BotController:
    def __init__(self, config, automator, monitor, emulator, vision):
        self.config = config
        self.logger = config.logger
        self.automator = automator
        self.monitor = monitor
        self.emulator = emulator
        self.vision = vision

        self.bot = telebot.TeleBot(config.bot_token)
        self.allowed_users = set()
        self.public_access = True
        self.request_queue = queue.Queue()
        self.users_lock = threading.Lock()

        self.load_users()
        self._register_handlers()

    def load_users(self):
        if os.path.exists(self.config.users_file):
            with open(self.config.users_file, "r") as f:
                self.allowed_users = set(json.load(f))

    def save_users(self):
        with open(self.config.users_file, "w") as f:
            json.dump(list(self.allowed_users), f)
            self.logger.info(f"User list updated and saved to {self.config.users_file}")

    def is_admin(self, message):
        return message.chat.id == self.config.admin_id

    def is_allowed(self, message):
        return message.chat.id in self.allowed_users or self.is_admin(message)

    def _register_handlers(self):
        @self.bot.message_handler(commands=["start"])
        def send_welcome(message):
            chat_id = message.chat.id
            self.logger.info(f"Received /start command from user: {chat_id}")
            if self.is_admin(message):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(
                    "📱 Open the app",
                    "❌️ Close the app",
                    "🔓 Unlock",
                    "📲 Open QR",
                    "📸 Take Screenshot",
                    "📸 Take QR Screenshot",
                    "🛑 Toggle Public Access",
                )
                self.bot.send_message(
                    chat_id,
                    "👑 Admin Dashboard\nUse /adduser <id>, /listusers or /removeuser <id> to manage access.",
                    reply_markup=markup,
                )
            elif self.is_allowed(message):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton("📸 Take QR Screenshot"))
                self.bot.send_message(
                    chat_id,
                    "Welcome! Press the button below to generate a QR code.",
                    reply_markup=markup,
                )
            else:
                self.logger.warning(f"Unauthorized access attempt by user: {chat_id}")
                self.bot.send_message(chat_id, "⛔ Unauthorized.")

        @self.bot.message_handler(commands=["adduser"], func=self.is_admin)
        def add_user(message):
            try:
                new_id = int(message.text.split()[1])
                with self.users_lock:
                    self.allowed_users.add(new_id)
                    self.save_users()
                self.logger.info(f"Admin added new user: {new_id}")
                self.bot.reply_to(message, f"✅ User {new_id} added.")
            except Exception:
                self.bot.reply_to(message, "⚠️ Usage: /adduser <telegram_id>")

        @self.bot.message_handler(commands=["listusers"], func=self.is_admin)
        def list_users(message):
            if not self.allowed_users:
                self.bot.reply_to(
                    message, "👥 The allowed users list is currently empty."
                )
                return
            user_list = "\n".join([f"• {uid}" for uid in self.allowed_users])
            self.bot.reply_to(
                message, f"👥 Allowed Users ({len(self.allowed_users)}):\n\n{user_list}"
            )

        @self.bot.message_handler(commands=["removeuser"], func=self.is_admin)
        def remove_user(message):
            rem_id = None
            try:
                rem_id = int(message.text.split()[1])
                with self.users_lock:
                    self.allowed_users.remove(rem_id)
                    self.save_users()
                self.logger.info(f"Admin removed user: {rem_id}")
                self.bot.reply_to(message, f"🗑️ User {rem_id} removed.")
            except KeyError:
                self.bot.reply_to(
                    message,
                    f"🛑 User {rem_id} does not exist in the allowed users list.",
                )
            except Exception:
                self.bot.reply_to(message, "⚠️ Usage: /removeuser <telegram_id>")

        @self.bot.message_handler(
            func=lambda m: m.text == "🛑 Toggle Public Access" and self.is_admin(m)
        )
        def toggle_access(message):
            self.public_access = not self.public_access
            status = "🟢 ENABLED" if self.public_access else "🔴 DISABLED"
            self.logger.info(f"Admin toggled public access: {status}")
            self.bot.reply_to(message, f"Public access is now {status}.")

        @self.bot.message_handler(
            func=lambda m: m.text == "📸 Take QR Screenshot" and self.is_allowed(m)
        )
        def handle_user_screenshot(message):
            self.monitor.update_activity()
            chat_id = message.chat.id
            if not self.public_access:
                self.bot.reply_to(
                    message, "⚠️ The bot is currently locked by the admin."
                )
                return
            self.bot.reply_to(
                message, "⏳ Added to the processing queue. Please wait..."
            )
            self.request_queue.put(chat_id)

        @self.bot.message_handler(
            func=lambda m: m.text == "❌️ Close the app" and self.is_admin(m)
        )
        def handle_close_app(message):
            with self.emulator.lock:
                self.monitor.update_activity()
                self.emulator.wake_if_needed(
                    lambda msg: self.bot.send_message(message.chat.id, msg)
                )
                self.bot.send_message(message.chat.id, "🧹 Closing the app...")
                if self.emulator.execute(
                    ["shell", "am", "force-stop", self.config.app_name], delay=1.0
                ):
                    self.bot.send_message(
                        message.chat.id, "✅ App closed successfully."
                    )
                else:
                    self.bot.send_message(
                        message.chat.id, "❌ Failed to close the app."
                    )

        @self.bot.message_handler(
            func=lambda m: m.text == "📱 Open the app" and self.is_admin(m)
        )
        def handle_open_app(message):
            with self.emulator.lock:
                self.monitor.update_activity()
                self.emulator.wake_if_needed(
                    lambda msg: self.bot.send_message(message.chat.id, msg)
                )
                self.bot.send_message(message.chat.id, "🚀 Opening the app...")
                if self.emulator.execute(
                    ["shell", "monkey", "-p", self.config.app_name, "1"], delay=2.0
                ):
                    self.bot.send_message(
                        message.chat.id, "✅ App opened successfully."
                    )
                else:
                    self.bot.send_message(message.chat.id, "❌ Failed to open the app.")

        @self.bot.message_handler(
            func=lambda m: m.text == "🔓 Unlock" and self.is_admin(m)
        )
        def handle_unlock(message):
            with self.emulator.lock:
                self.monitor.update_activity()
                self.emulator.wake_if_needed(
                    lambda msg: self.bot.send_message(message.chat.id, msg)
                )
                self.bot.send_message(message.chat.id, "🔐 Unlocking...")
                success = self.emulator.execute(
                    ["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5
                )
                for digit in str(self.config.app_pin):
                    if digit in self.config.pin_coords:
                        x, y = self.config.pin_coords[digit]
                        if not self.emulator.execute(
                            ["shell", "input", "tap", x, y], delay=0.3, silent=True
                        ):
                            success = False
                if success:
                    self.bot.send_message(
                        message.chat.id, "✅ App unlocked successfully."
                    )
                else:
                    self.bot.send_message(
                        message.chat.id, "❌ Failed to unlock the app."
                    )

        @self.bot.message_handler(
            func=lambda m: m.text == "📲 Open QR" and self.is_admin(m)
        )
        def handle_just_qr(message):
            with self.emulator.lock:
                self.monitor.update_activity()
                self.emulator.wake_if_needed(
                    lambda msg: self.bot.send_message(message.chat.id, msg)
                )
                self.bot.send_message(
                    message.chat.id, "🧭 Navigating directly to QR code..."
                )
                step1 = self.emulator.execute(
                    ["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=0.5
                )
                step2 = self.emulator.execute(
                    ["shell", "input", "tap", "272", "172"], delay=1.5
                )
                if step1 and step2:
                    self.bot.send_message(
                        message.chat.id, "✅ QR Code opened successfully."
                    )
                else:
                    self.bot.send_message(message.chat.id, "❌ Failed to open QR code.")

        @self.bot.message_handler(
            func=lambda m: m.text == "📸 Take Screenshot" and self.is_admin(m)
        )
        def handle_screenshot_command(message):
            with self.emulator.lock:
                self.monitor.update_activity()
                self.emulator.wake_if_needed(
                    lambda msg: self.bot.send_message(message.chat.id, msg)
                )
                img_path = self.vision.capture_screenshot(mode="full")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as photo:
                        self.bot.send_photo(message.chat.id, photo)
                    os.remove(img_path)

    def _queue_worker(self):
        self.logger.info("Task queue worker initialized.")
        while True:
            chat_id = self.request_queue.get()
            self.logger.info(f"Dequeued request for user {chat_id}. Processing...")
            try:
                if not self.public_access:
                    self.bot.send_message(
                        chat_id,
                        "⚠️ The admin has currently paused bot access. Try again later.",
                    )
                else:

                    def notify(msg):
                        self.bot.send_message(chat_id, msg)

                    def send_photo(path):
                        with open(path, "rb") as photo:
                            self.bot.send_photo(chat_id, photo)

                    self.automator.process_screenshot_request(notify, send_photo)
            except Exception:
                self.logger.exception(
                    f"Queue worker failed while processing user {chat_id}."
                )
                self.bot.send_message(
                    chat_id, "❌ An internal error occurred processing your request."
                )
            finally:
                self.request_queue.task_done()
                self.logger.info(f"Finished handling request for user {chat_id}.")

    def start(self):
        threading.Thread(target=self._queue_worker, daemon=True).start()
        self.logger.info("Bot is starting up and polling Telegram...")
        self.bot.infinity_polling()
