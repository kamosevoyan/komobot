import io
import subprocess
from typing import Literal

import cv2
import mss
import numpy as np

try:
    from pyzbar.pyzbar import decode as zbar_decode
except ImportError:
    zbar_decode = None


class VisionEngine:
    def __init__(self, config):
        self.config = config
        self.logger = config.logger

    def get_window_geometry(self) -> dict[str, int] | None:
        try:
            output = subprocess.check_output(["wmctrl", "-lG"]).decode("utf-8")
            for line in output.splitlines():
                if self.config.emulator_title in line:
                    parts = line.split(None, 7)
                    if len(parts) >= 8:
                        w, h = (int(parts[4]), int(parts[5]))
                        if 100 < w < 1200 and h > 100:
                            return {
                                "id": parts[0],
                                "left": int(parts[2]),
                                "top": int(parts[3]),
                                "width": w,
                                "height": h,
                            }
        except Exception:
            self.logger.exception("Error reading window geometry")
        return None

    def capture_screenshot(
        self, mode: Literal["qr", "full"] = "qr"
    ) -> io.BytesIO | None:
        self.logger.info(f"Initiating screenshot capture in '{mode}' mode.")
        monitor = self.get_window_geometry()
        if not monitor:
            return None

        with mss.MSS() as sct:
            sct_img = sct.grab(monitor)
            img = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape(
                sct_img.height, sct_img.width, 4
            )[5:-25, ...]
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if mode == "full":
            return self._encode_png(img)

        x_min = 60
        y_min = 180 - 25
        x_max = 260
        y_max = 370 - 25

        cropped_img = img[y_min:y_max, x_min:x_max]
        return self._encode_png(cropped_img)

    def _encode_png(self, img: np.ndarray) -> io.BytesIO | None:
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            self.logger.error("Failed to encode screenshot to PNG.")
            return None
        return io.BytesIO(buf.tobytes())
