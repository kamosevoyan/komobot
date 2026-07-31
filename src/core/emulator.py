import subprocess
import threading
import time


class EmulatorController:
    def __init__(self, config):
        self.config = config
        self.logger = config.logger
        self.lock = threading.Lock()
        self.is_deep_sleeping = False

    def execute(self, args, delay=0.5, silent=False, capture_output=False):
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
                self.logger.error(f"ADB command failed: {cmd_str} | Error: {e.stderr.strip()}")
            return None if capture_output else False
        except Exception as e:
            if not silent:
                self.logger.exception(f"Unexpected error running ADB: {cmd_str}")
            return None if capture_output else False

    def wake_if_needed(self, notify_callback=None):
        if self.is_deep_sleeping:
            if notify_callback:
                notify_callback("🥱 Waking up the emulator from deep sleep. This will take ~15 seconds...")
            self.logger.info("Waking up emulator from deep sleep...")

            with open(self.config.emu_args_path, "r") as handler:
                args = handler.read().split()

            args = ["emulator", "-no-snapshot-save", "-snapshot", "smart_snapshot", *args]

            subprocess.Popen(args)
            try:
                subprocess.run(["adb", "wait-for-device"], check=True)
            except subprocess.CalledProcessError:
                self.logger.error("Failed to wait for device")

            self.execute(["kill-server"], silent=True)
            self.execute(["start-server"], silent=True)
            self.is_deep_sleeping = False
            self.logger.info("Emulator is fully awake.")

    def check_app_state(self):
        res = self.execute(["shell", "dumpsys", "activity", "activities"], capture_output=True, silent=True)
        if not res or self.config.app_name not in res:
            return "closed"

        is_foreground = False
        for line in res.splitlines():
            if ("mResumedActivity" in line or "topResumedActivity" in line) and self.config.app_name in line:
                is_foreground = True
                break

        if not is_foreground:
            return "minimized"

        ui_res = self.execute(
            ["shell", "uiautomator dump /sdcard/view.xml >/dev/null 2>&1 && cat /sdcard/view.xml"],
            capture_output=True,
            silent=True,
        )
        content = ui_res if ui_res else ""

        if "Please enter PIN code" in content:
            return "locked"
        if "Buy tickets" in content:
            return "qr_section"
        return "ready"
