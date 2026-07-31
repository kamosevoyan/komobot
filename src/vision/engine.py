import subprocess
import tempfile
import uuid

import cv2
import mss
import mss.tools
import numpy as np

try:
    from pyzbar.pyzbar import decode as zbar_decode
except ImportError:
    zbar_decode = None


class VisionEngine:
    def __init__(self, config):
        self.config = config
        self.logger = config.logger

    def get_window_geometry(self):
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

    def capture_screenshot(self, mode="qr"):
        self.logger.info(f"Initiating screenshot capture in '{mode}' mode.")
        monitor = self.get_window_geometry()
        if not monitor:
            return None

        screenshot_path = f"{tempfile.gettempdir()}/emu_screenshot_{uuid.uuid4().hex}.png"
        with mss.MSS() as sct:
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)

        if mode == "full":
            return screenshot_path

        try:
            img = cv2.imread(screenshot_path)
            bbox = self._locate_qr(img)

            if bbox is not None:
                x_min = max(0, min(bbox[:, 0]) - 20)
                y_min = max(0, min(bbox[:, 1]) - 20)
                x_max = min(img.shape[1], max(bbox[:, 0]) + 20)
                y_max = min(img.shape[0], max(bbox[:, 1]) + 20)
                cropped_img = img[y_min:y_max, x_min:x_max]
                cv2.imwrite(screenshot_path, cropped_img)
                return screenshot_path

            self.logger.warning("QR Code not detected in screenshot.")
            return None
        except Exception:
            self.logger.exception("Failed to process QR code.")
            return None

    def _locate_qr(self, img):
        if zbar_decode is not None:
            results = zbar_decode(img)
            if results:
                rect = results[0].rect
                pts = [
                    (rect.left, rect.top),
                    (rect.left + rect.width, rect.top),
                    (rect.left + rect.width, rect.top + rect.height),
                    (rect.left, rect.top + rect.height),
                ]
                return cv2.convexHull(np.array(pts)).reshape(-1, 2)

        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(img)
        if bbox is not None:
            return bbox[0].astype(int)
        return None
