import random
import threading
import time


class SystemMonitor:
    def __init__(self, config, emulator):
        self.config = config
        self.emulator = emulator
        self.logger = config.logger
        self.last_interaction_time = time.time()

    def update_activity(self):
        self.last_interaction_time = time.time()

    def _inactivity_loop(self):
        self.logger.info("Inactivity monitor initialized.")
        while True:
            time.sleep(60)
            inactive_time = time.time() - self.last_interaction_time

            if inactive_time > self.config.deep_sleep_time and not self.emulator.is_deep_sleeping:
                self.logger.info("Deep sleep threshold reached. Shutting down emulator to free RAM...")
                with self.emulator.lock:
                    self.emulator.execute(["emu", "kill"])
                    self.emulator.is_deep_sleeping = True
            elif inactive_time > self.config.soft_sleep_time and not self.emulator.is_deep_sleeping:
                self.logger.info("Inactivity limit reached. Hard locking device...")
                with self.emulator.lock:
                    self.emulator.execute(["shell", "am", "force-stop", self.config.app_name])
                    self.emulator.execute(["shell", "input", "keyevent", "3"])
                    self.logger.info("Inactivity lock sequence executed.")

    def _keep_alive_loop(self):
        self.logger.info("Hardware key keep-alive initialized.")
        while True:
            if not self.emulator.is_deep_sleeping:
                try:
                    self.emulator.execute(["shell", "input", "keyevent", "24"], delay=0.5, silent=True)
                    self.emulator.execute(["shell", "input", "keyevent", "25"], delay=0.0, silent=True)
                except Exception as e:
                    self.logger.error(f"Keep-alive error: {e}")
            time.sleep(random.uniform(20.0, 45.0))

    def start(self):
        if self.config.boot_mode != "cold":
            threading.Thread(target=self._keep_alive_loop, daemon=True).start()
            threading.Thread(target=self._inactivity_loop, daemon=True).start()
        else:
            self.logger.info("🧊 Cold start mode: Inactivity monitor (sleeps) and keep-alive are disabled.")
