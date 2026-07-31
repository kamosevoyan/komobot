import subprocess
import tempfile

import cv2
import mss
import mss.tools


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
        except Exception as e:
            self.logger.error(f"Error reading window geometry: {e}")
        return None

    def capture_screenshot(self, mode="qr"):
        self.logger.info(f"Initiating screenshot capture in '{mode}' mode.")
        monitor = self.get_window_geometry()
        if not monitor:
            return None

        with mss.MSS() as sct, tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            sct_img = sct.grab(monitor)
            image_path = temp_file.name
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=image_path)
            self.logger.info(f"Saving the screenshot at path {image_path}")

        if mode == "full":
            return image_path

        try:
            img = cv2.imread(image_path)
            detector = cv2.QRCodeDetector()
            data, bbox, straight_qrcode = detector.detectAndDecode(img)

            if bbox is not None:
                pts = bbox[0].astype(int)
                x_min = max(0, min(pts[:, 0]) - 20)
                y_min = max(0, min(pts[:, 1]) - 20)
                x_max = min(img.shape[1], max(pts[:, 0]) + 20)
                y_max = min(img.shape[0], max(pts[:, 1]) + 20)
                cropped_img = img[y_min:y_max, x_min:x_max]
                cv2.imwrite(image_path, cropped_img)
                return image_path

            self.logger.warning("QR Code not detected in screenshot.")
            return None
        except Exception as e:
            self.logger.exception("Failed to process QR code.")
            return None
