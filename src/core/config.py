import logging
import os


class AppConfig:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.app_pin = os.getenv("APP_PIN")
        self.admin_id = int(os.getenv("ADMIN_ID", 0))
        self.boot_mode = os.getenv("BOOT_MODE", "prod")
        self.app_name = os.getenv("APP_NAME")
        self.log_dir = "./sodom"
        self.deep_sleep_time = 3600
        self.soft_sleep_time = 300
        self.emulator_title = "Android Emulator"
        self.users_file = "/root/.android/allowed_users.json"
        self.emu_args_path = "src/core/emu_args.txt"

        self.pin_coords = {
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

        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)-8s | %(threadName)-12s | %(message)s",
            handlers=[
                logging.FileHandler(
                    f"{self.log_dir}/bot_activity.log", encoding="utf-8"
                ),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger("komobot")
