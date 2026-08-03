import time
from typing import Callable

from ..core import AppConfig, EmulatorController
from ..vision import VisionEngine


class AppAutomator:
    def __init__(
        self, config: AppConfig, emulator: EmulatorController, vision: VisionEngine
    ):
        self.config = config
        self.emulator = emulator
        self.vision = vision
        self.logger = config.logger

    def process_screenshot_request(
        self,
        notify_callback: Callable[[str], None],
        send_photo_callback: Callable[[str], None],
    ) -> None:
        notify_callback("🔍 Checking app status...")
        with self.emulator.lock:
            self.emulator.wake_if_needed(notify_callback)
            self.emulator.execute(
                ["shell", "input", "keyevent", "KEYCODE_WAKEUP"], delay=1.0
            )

            state = self.emulator.check_app_state()

            if state == "minimized":
                notify_callback("🔄 App in background. Restoring...")
                self.emulator.execute(
                    ["shell", "monkey", "-p", self.config.app_name, "1"], delay=1.0
                )
                state = self.emulator.check_app_state()
            elif state == "closed":
                notify_callback("🚀 Launching app...")
                self.emulator.execute(
                    ["shell", "monkey", "-p", self.config.app_name, "1"], delay=1.0
                )
                state = "locked"

            if state == "locked":
                notify_callback("🔐 App locked. Entering PIN...")
                for digit in str(self.config.app_pin):
                    if digit in self.config.pin_coords:
                        x, y = self.config.pin_coords[digit]
                        self.emulator.execute(
                            ["shell", "input", "tap", x, y], delay=0.2, silent=True
                        )
                time.sleep(1.5)
                state = "ready"

            if state == "ready":
                notify_callback("📲 Generating QR...")
                self.emulator.execute(["shell", "input", "tap", "40", "600"], delay=1.0)
                self.emulator.execute(
                    ["shell", "input", "tap", "272", "172"], delay=1.0
                )
                state = "qr_section"

            if state == "qr_section":
                notify_callback("📸 Capturing...")
                photo_data = self.vision.capture_screenshot(mode="qr")
                if photo_data:
                    send_photo_callback(photo_data)
                else:
                    notify_callback("❌ Capture error.")
