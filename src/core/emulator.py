import subprocess
import threading
import time
from typing import Callable, Literal

import uiautomator2 as u2

from ..core import AppConfig


class EmulatorController:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = config.logger
        self.lock = threading.Lock()
        self.is_deep_sleeping = False
        self.daemon = u2.connect()

    def execute(
        self,
        args: list[str],
        delay: float = 0.5,
        silent: bool = False,
        capture_output: bool = False,
    ) -> None:
        cmd = ["adb"] + args
        cmd_str = " ".join(cmd)
        if not silent:
            self.logger.debug(f"Executing: {cmd_str}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if delay > 0:
                time.sleep(delay)
            if capture_output:
                return result.stdout
            return True
        except subprocess.CalledProcessError as e:
            if not silent:
                self.logger.error(
                    f"ADB command failed: {cmd_str} | Error: {e.stderr.strip()}"
                )
            return None if capture_output else False
        except Exception:
            if not silent:
                self.logger.exception(f"Unexpected error running ADB: {cmd_str}")
            return None if capture_output else False

    def wake_if_needed(self, notify_callback: Callable[[str], None] = None) -> None:
        if self.is_deep_sleeping:
            if notify_callback:
                notify_callback(
                    "🥱 Waking up the emulator from deep sleep. This will take ~15 seconds..."
                )
            self.logger.info("Waking up emulator from deep sleep...")

            with open(self.config.emu_args_path, "r") as handler:
                args = handler.read().split()

            args = [
                "emulator",
                "-no-snapshot-save",
                "-snapshot",
                self.config.snapshot_name,
                *args,
            ]

            subprocess.Popen(args)
            try:
                subprocess.run(["adb", "wait-for-device"], check=True)
            except subprocess.CalledProcessError:
                self.logger.error("Failed to wait for device")

            self.execute(["kill-server"], silent=True)
            self.execute(["start-server"], silent=True)
            self.is_deep_sleeping = False
            self.logger.info("Emulator is fully awake.")

    def check_app_state(self) -> str:
        try:
            current_app = self.daemon.app_current()
            is_foreground = current_app.get("package") == self.config.app_name
        except Exception:
            is_foreground = False

        if not is_foreground:
            pid_output = self.execute(
                ["shell", "pidof", self.config.app_name],
                delay=0,
                capture_output=True,
                silent=True,
            )
            return "minimized" if pid_output and pid_output.strip() else "closed"

        try:
            hierarchy = self.daemon.dump_hierarchy()
        except Exception:
            if self.daemon(text="Please enter PIN code").exists():
                return "locked"
            if self.daemon(text="Buy tickets").exists():
                return "qr_section"
            return "ready"

        if "Please enter PIN code" in hierarchy:
            return "locked"

        if "Buy tickets" in hierarchy:
            return "qr_section"

        return "ready"

    def get_bounds(self, selector):

        try:
            return selector.info["bounds"]
        except Exception:
            return None

    def wait_for_qr_gap(self, timeout=10, min_gap=100):

        start = time.time()

        while time.time() - start < timeout:
            submit = self.get_bounds(
                self.daemon(text="Submit the QR code to the scanner")
            )
            ticket = self.get_bounds(self.daemon(text="Ticket code"))

            if submit and ticket:
                gap = ticket["top"] - submit["bottom"]

                if gap >= min_gap:
                    return True

        return False

    def click_by_resource_id(self, resource_id: str, timeout: float = 5) -> bool:
        element = self.daemon(resourceId=resource_id)

        if not element.wait(timeout):
            return False

        element.click()

        return True
