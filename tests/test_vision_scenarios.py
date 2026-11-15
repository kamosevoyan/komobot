"""Scenario tests executing the generated vision BeanShell state machine."""

from __future__ import annotations

import struct
import unittest
from collections.abc import Callable

import generate_macro as gm
from tests.bsh_runtime import MockAndroidEnv, MockBitmap, run_bsh_script

VISION_SCRIPT = gm.build_vision_script()
POST_STEP_SCRIPT = gm.build_post_step_script()
ADMIN_ID = 111222333
USER_2 = 222333444
USER_3 = 555666777
LOCAL_VARS = {"bot_token": "test-token", "app_name": "ru.deltapay.puntopago.telcell"}


class ScreenFactory:
    """Synthetic bitmap builders for Virtual Master and Telcell Wallet screens."""

    @staticmethod
    def scaled(
        w: int, h: int, fill: tuple[int, int, int]
    ) -> tuple[MockBitmap, Callable[[int, int, int, int, int, int, int], None]]:
        bmp = MockBitmap(w, h, fill)

        def rect(x1: int, y1: int, x2: int, y2: int, r: int, g: int, b: int) -> None:
            bmp.fill_rect(
                (x1 * w) // 720,
                (y1 * h) // 1600,
                (x2 * w) // 720,
                (y2 * h) // 1600,
                r,
                g,
                b,
            )

        return bmp, rect

    @classmethod
    def vm_launcher(cls, show_enter: bool = True) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (18, 18, 18))
        if show_enter:
            rect(590, 230, 675, 270, 240, 240, 240)
        return bmp

    @classmethod
    def vm_popup(cls) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (220, 220, 220))
        rect(120, 580, 600, 1060, 28, 22, 34)
        return bmp

    @classmethod
    def vm_home(cls, slot: int = 1) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (60, 60, 60))
        rect(300, 750, 420, 850, 20, 20, 20)
        if slot == 1:
            rect(75, 355, 125, 405, 245, 95, 45)
        else:
            rect(75, 115, 125, 168, 245, 95, 45)
        return bmp

    @classmethod
    def vm_recents(
        cls, *, has_card: bool = True, floating_ball: bool = False
    ) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (218, 217, 228))
        if has_card:
            rect(124, 220, 592, 1260, 240, 242, 244)
        if floating_ball:
            rect(665, 760, 715, 840, 253, 253, 253)
        return bmp

    @classmethod
    def pin_screen(
        cls, *, spinner: bool = False, w: int = 720, h: int = 1600
    ) -> MockBitmap:
        # Note: (240, 242, 244) satisfies isPinGray() and isWhite() across the grid,
        # matching the real device PIN screen.
        bmp, rect = cls.scaled(w, h, (240, 242, 244))
        rect(280, 120, 440, 220, 245, 95, 50)
        if spinner:
            rect(330, 680, 390, 715, 240, 90, 60)
        return bmp

    @classmethod
    def dashboard(cls, mode: str = "low") -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (230, 232, 235))
        rect(0, 1350, 720, 1520, 255, 255, 255)
        rect(340, 1355, 380, 1390, 245, 115, 70)
        if mode == "skeleton":
            for x, y in ((200, 300), (580, 415), (360, 800)):
                rect(x - 10, y - 10, x + 10, y + 10, 250, 250, 250)
        elif mode == "low":
            rect(55, 1050, 105, 1100, 240, 110, 55)
        elif mode == "high":
            rect(55, 790, 105, 840, 240, 110, 55)
        elif mode == "unloaded":
            rect(340, 1080, 380, 1120, 250, 250, 250)
        return bmp

    @classmethod
    def buy_ticket_tab(cls) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (255, 255, 255))
        rect(80, 225, 120, 245, 245, 115, 70)
        rect(260, 225, 295, 245, 252, 252, 252)
        return bmp

    @classmethod
    def ticket_list(cls, *, card_loaded: bool = True) -> MockBitmap:
        bmp, rect = cls.scaled(720, 1600, (245, 245, 246))
        rect(260, 225, 295, 245, 245, 115, 70)
        rect(80, 225, 120, 245, 252, 252, 252)
        if card_loaded:
            rect(200, 340, 520, 460, 255, 255, 255)
        return bmp

    @classmethod
    def qr_modal(
        cls, *, loaded: bool = True, w: int = 720, h: int = 1600
    ) -> MockBitmap:
        bmp, rect = cls.scaled(w, h, (40, 40, 40))
        rect(70, 140, 650, 1100, 250, 250, 250)
        if loaded:
            for y in range(510, 831, 12):
                for x in range(200, 521, 12):
                    if ((x + y) // 12) % 2 == 0:
                        rect(x, y, x + 5, y + 5, 10, 10, 10)
        return bmp

    @classmethod
    def white_blank(cls) -> MockBitmap:
        return MockBitmap(720, 1600, (252, 252, 252))

    @classmethod
    def dense_white_products_screen(cls) -> MockBitmap:
        # Leaves (360,240), (360,800), (550,485) white like ProductsFragment,
        # while placing multi-column UI cards/text along x=120/240/480/600.
        bmp, rect = cls.scaled(720, 1600, (252, 252, 252))
        for x in (120, 240, 480, 600):
            for y in (240, 390, 540, 690, 840):
                rect(x - 15, y - 15, x + 15, y + 15, 90, 100, 110)
        return bmp


class TestVisionScenarios(unittest.TestCase):
    """Test Vision state transitions, regressions, queueing, and cleanup."""

    def setUp(self) -> None:
        self.env = MockAndroidEnv(now_ms=1794735000000)
        self._ss_seq = 0
        self._seed_active_run()

    def _seed_active_run(
        self,
        *,
        active_chat_id: int = ADMIN_ID,
        mode: str = "qr",
        queue: list[dict] | None = None,
        step_count: int = 0,
        qr_was_closed: bool = False,
        progress_pct: int = 0,
    ) -> None:
        self.env.write_config(
            {
                "admin_id": ADMIN_ID,
                "allowed_users": [ADMIN_ID, USER_2, USER_3],
                "public_access": True,
                "busy_until": self.env.now_ms + 45000,
                "last_update_id": 500,
                "active_chat_id": active_chat_id,
                "status_message_id": 1001,
                "capture_mode": mode,
                "queue": queue or [],
                "qr_was_closed": qr_was_closed,
                "step_count": step_count,
                "other_count": 0,
                "white_count": 0,
                "loading_count": 0,
                "progress_pct": progress_pct,
                "last_state": "INIT",
                "run_start_ms": self.env.now_ms,
            }
        )

    def _step(
        self, bmp: MockBitmap | None, *, size: int = 120_000, with_thumb: bool = True
    ) -> str:
        self._ss_seq += 1
        self.env.advance_time(200)
        self.env.add_screenshot(
            f"Screenshot_{self._ss_seq:03d}_Virtual Master.jpg",
            bmp,
            size=size,
            with_thumbnail=with_thumb,
        )
        cmd = run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS)
        if cmd not in ("DONE", "DONE_RESET"):
            run_bsh_script(
                POST_STEP_SCRIPT,
                self.env,
                {"bot_token": LOCAL_VARS["bot_token"], "step_cmd": cmd},
            )
        return cmd

    def test_cold_start_full_navigation_to_qr_sent(self) -> None:
        expected_steps = [
            (ScreenFactory.vm_launcher(True), "CLICK_ENTER", "VM_LAUNCHER"),
            (ScreenFactory.vm_home(slot=1), "LAUNCH_1", "VM_HOME_1"),
            (ScreenFactory.pin_screen(spinner=True), "WAIT", "PIN_SPINNER"),
            (ScreenFactory.pin_screen(spinner=False), "ENTER_PIN", "PIN_PAD"),
            (ScreenFactory.dashboard("skeleton"), "WAIT", "DASH_LOADING"),
            (ScreenFactory.dashboard("low"), "CLICK_TRANSPORT_LOW", "DASHBOARD_LOW"),
            (ScreenFactory.buy_ticket_tab(), "CLICK_AVAILABLE_TAB", "BUY_TICKET_TAB"),
            (ScreenFactory.ticket_list(card_loaded=False), "WAIT", "TICKET_LOADING"),
            (
                ScreenFactory.ticket_list(card_loaded=True),
                "CLICK_TICKET_ROW",
                "TICKET_LIST",
            ),
            (ScreenFactory.qr_modal(loaded=False), "WAIT", "QR_LOADING"),
            (ScreenFactory.qr_modal(loaded=True), "DONE", "QR_SENT"),
        ]
        for bmp, expected_cmd, expected_state in expected_steps:
            cmd = self._step(bmp)
            cfg = self.env.read_config()
            self.assertEqual(cmd, expected_cmd)
            self.assertEqual(cfg["last_state"], expected_state)
            self.assertTrue(bmp.recycled)

        final_cfg = self.env.read_config()
        self.assertEqual(final_cfg["busy_until"], 0)
        self.assertEqual(final_cfg["step_count"], len(expected_steps))
        self.assertEqual(final_cfg["white_count"], 0)
        self.assertEqual(final_cfg["loading_count"], 0)
        self.assertEqual(final_cfg["other_count"], 0)

        photos = [c for c in self.env.tg_calls if c["method"] == "sendPhoto"]
        self.assertEqual(len(photos), 1)
        self.assertEqual(int(photos[0]["chat_id"]), ADMIN_ID)
        png = photos[0]["photo_bytes"]
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        w, h = struct.unpack("!II", png[16:24])
        self.assertEqual((w, h), (460, 460))
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls[-2:]],
            ["sendPhoto", "deleteMessage"],
        )
        self.assertEqual([k for k in self.env.files if "Screenshots" in k], [])

    def test_regression_pin_screen_with_white_grid_never_matches_white_loading(
        self,
    ) -> None:
        cmd = self._step(ScreenFactory.pin_screen(spinner=False))
        cfg = self.env.read_config()
        self.assertEqual(cmd, "ENTER_PIN")
        self.assertEqual(cfg["last_state"], "PIN_PAD")
        self.assertEqual(cfg["white_count"], 0)

    def test_regression_unloaded_dashboard_waits_five_ticks_before_fallback(
        self,
    ) -> None:
        for expected_count in (1, 2, 3, 4, 5):
            self.assertEqual(self._step(ScreenFactory.dashboard("unloaded")), "WAIT")
            cfg = self.env.read_config()
            self.assertEqual(cfg["last_state"], "DASH_LOADING")
            self.assertEqual(cfg["loading_count"], expected_count)

        # On 6th tick without icons, falls back to LOW tap and clears wait counters
        self.assertEqual(
            self._step(ScreenFactory.dashboard("unloaded")), "CLICK_TRANSPORT_LOW"
        )
        self.assertEqual(self.env.read_config()["last_state"], "DASHBOARD_LOW")
        self.assertEqual(self.env.read_config()["loading_count"], 0)

    def test_regression_white_loading_bounded_recovery_and_dense_screen_escape(
        self,
    ) -> None:
        # Blank white transition screen: 7x WAIT -> CLICK_BACK -> WAIT -> RESET_TO_HOME
        seq = [self._step(ScreenFactory.white_blank()) for _ in range(10)]
        self.assertEqual(seq, ["WAIT"] * 7 + ["CLICK_BACK", "WAIT", "RESET_TO_HOME"])
        cfg = self.env.read_config()
        self.assertEqual(cfg["last_state"], "WHITE_LOADING")
        self.assertEqual(cfg["white_count"], 0)

        # Dense multi-column UI (ProductsFragment): avoids WHITE_LOADING loop
        other_seq = [
            self._step(ScreenFactory.dense_white_products_screen()) for _ in range(5)
        ]
        self.assertEqual(
            other_seq, ["WAIT", "WAIT", "CLICK_BACK", "WAIT", "RESET_TO_HOME"]
        )
        self.assertEqual(self.env.read_config()["last_state"], "OTHER")
        self.assertEqual(self.env.read_config()["other_count"], 0)

    def test_stale_qr_refreshed_on_step1_and_sent_on_step2(self) -> None:
        cmd1 = self._step(ScreenFactory.qr_modal(loaded=True))
        cfg1 = self.env.read_config()
        self.assertEqual(cmd1, "CLOSE_MODAL")
        self.assertEqual(cfg1["last_state"], "STALE_QR")
        self.assertTrue(cfg1["qr_was_closed"])
        self.assertEqual(
            [c for c in self.env.tg_calls if c["method"] == "sendPhoto"], []
        )

        # Re-open ticket list -> fresh QR on step 2 uploads cleanly
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "CLICK_TICKET_ROW"
        )
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "DONE")
        self.assertEqual(self.env.read_config()["last_state"], "QR_SENT")
        self.assertEqual(
            len([c for c in self.env.tg_calls if c["method"] == "sendPhoto"]), 1
        )

    def test_multi_user_queue_handoff_delivers_all_qrs(self) -> None:
        self._seed_active_run(
            step_count=1,
            queue=[
                {"chat_id": USER_2, "status_message_id": 2002},
                {"chat_id": USER_3, "status_message_id": 3003},
            ],
        )
        # First QR pops USER_2 and returns CLOSE_MODAL
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        cfg1 = self.env.read_config()
        self.assertEqual(cfg1["last_state"], "NEXT_IN_QUEUE")
        self.assertEqual(cfg1["active_chat_id"], USER_2)
        self.assertEqual(cfg1["step_count"], 2)
        self.assertTrue(cfg1["qr_was_closed"])
        self.assertEqual(len(cfg1["queue"]), 1)

        # Second QR pops USER_3
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        cfg2 = self.env.read_config()
        self.assertEqual(cfg2["active_chat_id"], USER_3)
        self.assertEqual(cfg2["queue"], [])

        # Third QR completes run with DONE
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "DONE")
        cfg3 = self.env.read_config()
        self.assertEqual(cfg3["last_state"], "QR_SENT")
        self.assertEqual(cfg3["busy_until"], 0)
        photos = [c for c in self.env.tg_calls if c["method"] == "sendPhoto"]
        self.assertEqual(
            [int(p["chat_id"]) for p in photos], [ADMIN_ID, USER_2, USER_3]
        )

    def test_bounded_loading_recovery_for_qr_spinner_and_ticket_loading(self) -> None:
        for loader in (
            lambda: ScreenFactory.qr_modal(loaded=False),
            lambda: ScreenFactory.pin_screen(spinner=True),
            lambda: ScreenFactory.ticket_list(card_loaded=False),
        ):
            self.setUp()
            self._seed_active_run(step_count=1)
            cmds = [self._step(loader()) for _ in range(12)]
            self.assertEqual(
                cmds, ["WAIT"] * 9 + ["CLICK_BACK", "WAIT", "RESET_TO_HOME"]
            )
            self.assertEqual(self.env.read_config()["loading_count"], 0)

    def test_reset_mode_popup_vm_loading_and_slot2_launch(self) -> None:
        self.assertEqual(self._step(ScreenFactory.vm_launcher(False)), "WAIT")
        self.assertEqual(self.env.read_config()["last_state"], "VM_LOADING")

        self.assertEqual(self._step(ScreenFactory.vm_popup()), "DISMISS_POPUP")
        self.assertEqual(self.env.read_config()["last_state"], "VM_POPUP")

        self.assertEqual(self._step(ScreenFactory.vm_home(slot=2)), "LAUNCH_2")
        self.assertEqual(self.env.read_config()["last_state"], "VM_HOME_2")

        self.assertEqual(
            self._step(ScreenFactory.dashboard("high")), "CLICK_TRANSPORT_HIGH"
        )
        self.assertEqual(self.env.read_config()["last_state"], "DASHBOARD_HIGH")

        # Full Option A reset flow: open Recents, kill card, relaunch to Ticket List
        self._seed_active_run(mode="reset")
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "OPEN_RECENTS"
        )
        self.assertEqual(self.env.read_config()["last_state"], "RESET_OPEN_RECENTS")
        # Second in-app tick waits rather than double-tapping Recents during animation
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "WAIT"
        )
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=True, floating_ball=True)),
            "SWIPE_KILL_RECENT",
        )
        self.assertEqual(self.env.read_config()["reset_kills"], 1)
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=False, floating_ball=True)),
            "RESET_TO_HOME",
        )
        self.assertEqual(self.env.read_config()["reset_stage"], 1)
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=2)), "LAUNCH_2")
        self.assertEqual(self.env.read_config()["reset_stage"], 2)
        self.assertEqual(self._step(ScreenFactory.white_blank()), "WAIT")
        self.assertEqual(self._step(ScreenFactory.pin_screen()), "ENTER_PIN")
        self.assertEqual(
            self._step(ScreenFactory.dashboard("low")), "CLICK_TRANSPORT_LOW"
        )
        self.assertEqual(
            self._step(ScreenFactory.buy_ticket_tab()), "CLICK_AVAILABLE_TAB"
        )
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=False)), "WAIT"
        )
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "DONE_RESET"
        )
        reset_cfg = self.env.read_config()
        self.assertEqual(reset_cfg["last_state"], "RESET")
        self.assertEqual(reset_cfg["busy_until"], 0)
        self.assertEqual(
            [c for c in self.env.tg_calls if c["method"] == "sendPhoto"], []
        )

    def test_reset_from_vm_home_qr_recents_escape_and_preemption(self) -> None:
        # Starting reset on VM_HOME checks Recents once before launching Telcell
        self._seed_active_run(mode="reset")
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=1)), "OPEN_RECENTS")
        self.assertEqual(self.env.read_config()["last_state"], "RESET_CHECK_RECENTS")
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=False)), "RESET_TO_HOME"
        )
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=1)), "LAUNCH_1")
        # Stale QR modal during reset is closed without uploading photo
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        self.assertEqual(self.env.read_config()["last_state"], "RESET_CLOSE_QR")
        self.assertEqual(
            [c for c in self.env.tg_calls if c["method"] == "sendPhoto"], []
        )
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "DONE_RESET"
        )

        # Regular QR run recovers cleanly from VM_RECENTS back to home
        self.setUp()
        self._seed_active_run(mode="qr")
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=True)), "RESET_TO_HOME"
        )
        self.assertEqual(self.env.read_config()["last_state"], "VM_RECENTS")

        # Cooperative preemption on shared single worker switches cleanly to reset
        self._seed_active_run(mode="reset")
        qr_vars = {**LOCAL_VARS, "msg_text": "/qr"}
        self.assertEqual(run_bsh_script(VISION_SCRIPT, self.env, qr_vars), "WAIT")
        self.assertEqual(
            run_bsh_script(
                POST_STEP_SCRIPT, self.env, {**qr_vars, "step_cmd": "ENTER_PIN"}
            ),
            "OK",
        )
        self.assertEqual(self.env.read_config()["last_state"], "NO_SCREENSHOT")

    def test_resolution_scaling_filtering_decode_err_and_http_error(self) -> None:
        # 1080x2400 scaling works for both PIN pad and QR modal crop (690x690)
        self._seed_active_run(step_count=1)
        self.assertEqual(
            self._step(ScreenFactory.pin_screen(w=1080, h=2400)), "ENTER_PIN"
        )
        self.env.http_status_overrides["sendPhoto"] = 500
        self.assertEqual(
            self._step(ScreenFactory.qr_modal(loaded=True, w=1080, h=2400)), "DONE"
        )
        photo = [c for c in self.env.tg_calls if c["method"] == "sendPhoto"][-1]
        w, h = struct.unpack("!II", photo["photo_bytes"][16:24])
        self.assertEqual((w, h), (690, 690))
        edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText"
        ]
        self.assertIn("Failed to upload QR (HTTP 500)", edits[-1])

        # Ignore tiny (<5KB) or stale screenshots and handle NO_SCREENSHOT / DECODE_ERR
        self.setUp()
        self.env.add_screenshot(
            "Screenshot_tiny.jpg", ScreenFactory.white_blank(), size=1000
        )
        self.env.add_screenshot(
            "Screenshot_old.jpg",
            ScreenFactory.white_blank(),
            size=100_000,
            mtime_ms=self.env.now_ms - 10_000,
        )
        self.assertEqual(run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS), "WAIT")
        self.assertEqual(self.env.read_config()["last_state"], "NO_SCREENSHOT")

        # Decode error still cleans up unreadable screenshot and trashed VM artifacts
        self.env.add_screenshot(
            ".trashed-123-Virtual Master.jpg",
            None,
            directory="/storage/emulated/0/DCIM/Screenshots",
        )
        self.assertEqual(self._step(None), "WAIT")
        self.assertEqual(self.env.read_config()["last_state"], "DECODE_ERR")
        self.assertNotIn(
            "/storage/emulated/0/DCIM/Screenshots/.trashed-123-Virtual Master.jpg",
            self.env.files,
        )

    def test_long_inactivity_full_cold_vm_and_telcell_boot_recovery(self) -> None:
        # Worst-case cold resume after LMKD/Phantom Process Killer eviction:
        # 1x NO_SCREENSHOT + VM launcher + 8x VM boot + popup + VM home
        # + 5x cold white splash + 3x PIN spinner + PIN pad
        # + 3x waking Wi-Fi dashboard + Transport -> Ticket -> QR (<= 32 steps).
        self.assertEqual(run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS), "WAIT")
        self.assertEqual(self.env.read_config()["last_state"], "NO_SCREENSHOT")

        cold_steps = [
            (ScreenFactory.vm_launcher(True), "CLICK_ENTER", "VM_LAUNCHER"),
            *[(ScreenFactory.vm_launcher(False), "WAIT", "VM_LOADING")] * 8,
            (ScreenFactory.vm_popup(), "DISMISS_POPUP", "VM_POPUP"),
            (ScreenFactory.vm_home(slot=1), "LAUNCH_1", "VM_HOME_1"),
            *[(ScreenFactory.white_blank(), "WAIT", "WHITE_LOADING")] * 5,
            *[(ScreenFactory.pin_screen(spinner=True), "WAIT", "PIN_SPINNER")] * 3,
            (ScreenFactory.pin_screen(spinner=False), "ENTER_PIN", "PIN_PAD"),
            *[(ScreenFactory.dashboard("unloaded"), "WAIT", "DASH_LOADING")] * 3,
            (ScreenFactory.dashboard("low"), "CLICK_TRANSPORT_LOW", "DASHBOARD_LOW"),
            (ScreenFactory.buy_ticket_tab(), "CLICK_AVAILABLE_TAB", "BUY_TICKET_TAB"),
            (ScreenFactory.ticket_list(card_loaded=False), "WAIT", "TICKET_LOADING"),
            (
                ScreenFactory.ticket_list(card_loaded=True),
                "CLICK_TICKET_ROW",
                "TICKET_LIST",
            ),
            (ScreenFactory.qr_modal(loaded=False), "WAIT", "QR_LOADING"),
            (ScreenFactory.qr_modal(loaded=True), "DONE", "QR_SENT"),
        ]
        for bmp, expected_cmd, expected_state in cold_steps:
            self.assertEqual(self._step(bmp), expected_cmd)
            self.assertEqual(self.env.read_config()["last_state"], expected_state)

        cfg = self.env.read_config()
        self.assertEqual(cfg["step_count"], 30)
        self.assertLessEqual(cfg["step_count"], 45)
        self.assertEqual(cfg["busy_until"], 0)
        self.assertEqual(
            len([c for c in self.env.tg_calls if c["method"] == "sendPhoto"]), 1
        )

    def test_private_frame_same_second_no_1s_sleep_and_http_keep_alive(self) -> None:
        # Consecutive private frames with identical 1s-quantized FUSE mtime must
        # resolve without blocking 1000ms, overlap intermediate edit into PostStep,
        # and leave Keep-Alive connections un-disconnected on clean responses.
        self._seed_active_run(step_count=0)
        fixed_sec_mtime = self.env.now_ms
        t_start = self.env.now_ms
        self.env.add_screenshot(
            "frame.png",
            ScreenFactory.ticket_list(card_loaded=True),
            mtime_ms=fixed_sec_mtime,
            directory="/storage/emulated/0/komobot_ss",
        )
        self.assertEqual(
            run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS), "CLICK_TICKET_ROW"
        )
        elapsed_vision1 = self.env.now_ms - t_start
        self.assertLess(elapsed_vision1, 100)
        self.assertNotIn("/storage/emulated/0/komobot_ss/frame.png", self.env.files)
        self.assertTrue(self.env.read_config()["last_ss_deleted"])
        # Status edit is deferred to POST_STEP_SCRIPT (zero pre-tap Telegram blocking)
        self.assertEqual(self.env.tg_calls, [])
        self.assertEqual(
            run_bsh_script(
                POST_STEP_SCRIPT,
                self.env,
                {"bot_token": LOCAL_VARS["bot_token"], "step_cmd": "CLICK_TICKET_ROW"},
            ),
            "OK",
        )
        self.assertEqual(len(self.env.tg_calls), 1)
        self.assertEqual(self.env.tg_calls[0]["method"], "editMessageText")

        t_step2 = self.env.now_ms
        self.env.add_screenshot(
            "frame.png",
            ScreenFactory.qr_modal(loaded=True),
            mtime_ms=fixed_sec_mtime,
            directory="/storage/emulated/0/komobot_ss",
        )
        self.assertEqual(run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS), "DONE")
        elapsed_vision2 = self.env.now_ms - t_step2
        self.assertLess(elapsed_vision2, 100)
        self.assertNotIn("/storage/emulated/0/komobot_ss/frame.png", self.env.files)
        for conn in self.env.http_connections:
            self.assertTrue(conn["stream_read"])
            self.assertTrue(conn["stream_closed"])
            self.assertFalse(conn["disconnected"])

    def test_regular_user_progress_bar_monotonic_and_admin_logs_preserved(self) -> None:
        self._seed_active_run(
            active_chat_id=USER_2,
            progress_pct=10,
            queue=[
                {"chat_id": ADMIN_ID, "status_message_id": 9001},
                {"chat_id": USER_3, "status_message_id": 9002},
            ],
        )

        # Navigate USER_2 through VM + Telcell + wait nudge + backward retry guard
        steps = [
            (ScreenFactory.vm_launcher(True), "CLICK_ENTER"),
            (ScreenFactory.vm_home(slot=1), "LAUNCH_1"),
            (ScreenFactory.white_blank(), "WAIT"),  # wait tick 1: no redundant edit
            (ScreenFactory.white_blank(), "WAIT"),  # wait tick 2: nudges to 40%
            (ScreenFactory.pin_screen(spinner=False), "ENTER_PIN"),
            (ScreenFactory.dashboard("low"), "CLICK_TRANSPORT_LOW"),
            # Simulated transient return to PIN screen must never move bar backward
            (ScreenFactory.pin_screen(spinner=False), "ENTER_PIN"),
            (ScreenFactory.buy_ticket_tab(), "CLICK_AVAILABLE_TAB"),
            (ScreenFactory.ticket_list(card_loaded=True), "CLICK_TICKET_ROW"),
        ]
        for bmp, expected_cmd in steps:
            self.assertEqual(self._step(bmp), expected_cmd)

        user2_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == USER_2
        ]
        self.assertEqual(
            user2_edits,
            [
                "⏳ Generating QR code...\n🟩🟩⬜⬜⬜⬜⬜⬜⬜⬜ 20%",
                "⏳ Generating QR code...\n🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜ 30%",
                "⏳ Generating QR code...\n🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%",
                "⏳ Generating QR code...\n🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜ 50%",
                "⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜ 60%",
                "⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜ 70%",
                "⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%",
            ],
        )

        # QR upload sends photo directly and deletes status without redundant 90% edit
        self.env.tg_calls.clear()
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        user2_qr_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == USER_2
        ]
        self.assertEqual(user2_qr_edits, [])
        deletes = [
            c["payload"]["chat_id"]
            for c in self.env.tg_calls
            if c["method"] == "deleteMessage"
        ]
        self.assertIn(USER_2, deletes)

        # Queued ADMIN_ID still received original text prompt
        admin_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == ADMIN_ID
        ]
        self.assertEqual(admin_edits, ["🔄 Generating QR code for your request..."])

        # ADMIN_ID ticket & QR keep detailed admin step logs; popping USER_3 starts 70%
        self.env.tg_calls.clear()
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "CLICK_TICKET_ROW"
        )
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        admin_step_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == ADMIN_ID
        ]
        self.assertEqual(admin_step_edits, ["🎫 Selecting ticket..."])
        user3_handoff = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == USER_3
        ]
        self.assertEqual(
            user3_handoff, ["⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜ 70%"]
        )

        # USER_3 finishes with 80% progress bar and photo upload (no internal logs)
        self.env.tg_calls.clear()
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "CLICK_TICKET_ROW"
        )
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "DONE")
        user3_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == USER_3
        ]
        self.assertEqual(
            user3_edits, ["⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%"]
        )
        for text in user2_edits + user2_qr_edits + user3_handoff + user3_edits:
            for leak in ("Virtual Master", "Telcell", "PIN", "Transport", "ticket"):
                self.assertNotIn(leak, text)

    def test_truncated_private_png_ignored_and_cleaned(self) -> None:
        """Truncated PNG without IEND must not decode black rows as VM_LAUNCHER."""
        self._seed_active_run()
        partial_bmp = MockBitmap(720, 1600, (0, 0, 0))
        partial_bmp.fill_rect(595, 235, 670, 265, 107, 146, 208)
        frame_path = self.env.add_screenshot(
            "frame.png",
            partial_bmp,
            size=131_326,
            directory="/storage/emulated/0/komobot_ss",
            truncated=True,
        )
        t0 = self.env.now_ms
        cmd = run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS)
        self.assertEqual(cmd, "WAIT")
        self.assertGreaterEqual(self.env.now_ms - t0, 1800)
        cfg = self.env.read_config()
        self.assertEqual(cfg["last_state"], "TRUNCATED_SS")
        self.assertTrue(cfg["last_ss_deleted"])
        self.assertNotIn(frame_path, self.env.files)

        self.env.add_screenshot(
            "frame.png",
            ScreenFactory.ticket_list(card_loaded=True),
            directory="/storage/emulated/0/komobot_ss",
        )
        t1 = self.env.now_ms
        cmd2 = run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS)
        self.assertEqual(cmd2, "CLICK_TICKET_ROW")
        self.assertLess(self.env.now_ms - t1, 100)
        self.assertEqual(self.env.read_config()["last_state"], "TICKET_LIST")

    def test_reverse_reset_to_queued_user_qr_upload_failure_and_step_cap(self) -> None:
        # 1. Reverse overlap: Admin Reset active while USER_2 is queued
        self._seed_active_run(
            mode="reset",
            active_chat_id=ADMIN_ID,
            queue=[{"chat_id": USER_2, "status_message_id": 7002}],
        )
        cfg = self.env.read_config()
        cfg["status_message_id"] = 7001
        self.env.write_config(cfg)
        self.assertEqual(self._step(ScreenFactory.vm_launcher(True)), "CLICK_ENTER")
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=1)), "OPEN_RECENTS")
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=True)), "SWIPE_KILL_RECENT"
        )
        self.assertEqual(
            self._step(ScreenFactory.vm_recents(has_card=False)), "RESET_TO_HOME"
        )
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=1)), "LAUNCH_1")
        self.assertEqual(
            self._step(ScreenFactory.pin_screen(spinner=False)), "ENTER_PIN"
        )
        self.assertEqual(
            self._step(ScreenFactory.dashboard("low")), "CLICK_TRANSPORT_LOW"
        )
        self.env.tg_calls.clear()
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "CLICK_TICKET_ROW"
        )

        # Admin reset message completes and popped USER_2 receives 80% progress bar
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertIn(
            {
                "chat_id": ADMIN_ID,
                "message_id": 7001,
                "text": "✅ VM app reset complete — Telcell restarted & ready.",
            },
            edits,
        )
        self.assertIn(
            {
                "chat_id": USER_2,
                "message_id": 7002,
                "text": "⏳ Generating QR code...\n🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%",
            },
            edits,
        )
        cfg = self.env.read_config()
        self.assertEqual(cfg["capture_mode"], "qr")
        self.assertEqual(cfg["active_chat_id"], USER_2)
        self.assertEqual(cfg["queue"], [])
        self.assertEqual(cfg["step_count"], 2)

        # 2. Regular user QR upload failure notifies Admin with HTTP status
        self.env.http_status_overrides["sendPhoto"] = 502
        self.env.tg_calls.clear()
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "DONE")
        user_edits = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "editMessageText" and c["payload"]["chat_id"] == USER_2
        ]
        self.assertEqual(user_edits, ["❌ Failed to upload QR. Please try again."])
        admin_sends = [
            c["payload"]["text"]
            for c in self.env.tg_calls
            if c["method"] == "sendMessage" and c["payload"]["chat_id"] == ADMIN_ID
        ]
        self.assertEqual(len(admin_sends), 1)
        self.assertIn(f"chat_id: {USER_2}", admin_sends[0])
        self.assertIn("HTTP 502", admin_sends[0])

        # 3. Per-request 95-step cap triggers ABORT_TIMEOUT inside 130-step loop
        self._seed_active_run(step_count=95)
        cfg_cap = self.env.read_config()
        cfg_cap["last_state"] = "WHITE_LOADING"
        self.env.write_config(cfg_cap)
        self.assertEqual(
            run_bsh_script(VISION_SCRIPT, self.env, LOCAL_VARS), "ABORT_TIMEOUT"
        )
        self.assertEqual(self.env.read_config()["step_count"], 95)
        self.assertEqual(self.env.read_config()["last_state"], "WHITE_LOADING")

        # 4. Cold VM boot in reset mode (after VM_LAUNCHER) does NOT fire
        # RESET_OPEN_RECENTS or early CLICK_BACK on VM splash/white frames
        self.setUp()
        self._seed_active_run(mode="qr", active_chat_id=USER_2, step_count=0)
        self.assertEqual(self._step(ScreenFactory.vm_launcher(True)), "CLICK_ENTER")
        self.assertTrue(self.env.read_config()["vm_booting"])
        # Simulate cooperative preemption to reset while VM splash / OTHER shows
        coop_cfg = self.env.read_config()
        coop_cfg["capture_mode"] = "reset"
        coop_cfg["active_chat_id"] = ADMIN_ID
        coop_cfg["run_start_ms"] = coop_cfg["run_start_ms"] + 500
        coop_cfg["step_count"] = 0
        self.env.write_config(coop_cfg)
        boot_splash = MockBitmap(720, 1600, (120, 130, 140))
        for _ in range(5):
            self.assertEqual(self._step(boot_splash), "WAIT")
            self.assertEqual(self.env.read_config()["last_state"], "OTHER")
        self.assertEqual(self._step(ScreenFactory.white_blank()), "WAIT")
        self.assertEqual(self.env.read_config()["last_state"], "WHITE_LOADING")
        # Once VM_HOME renders, vm_booting clears and Reset checks Recents cleanly
        self.assertEqual(self._step(ScreenFactory.vm_home(slot=1)), "OPEN_RECENTS")
        self.assertFalse(self.env.read_config()["vm_booting"])
        self.assertEqual(self.env.read_config()["last_state"], "RESET_CHECK_RECENTS")

        # Even if vm_booting was still set, a recognized Telcell screen
        # (such as TICKET_LIST) still triggers Phase 0 in-app intercept
        self.setUp()
        self._seed_active_run(mode="reset", step_count=1)
        boot_telcell = self.env.read_config()
        boot_telcell["vm_booting"] = True
        self.env.write_config(boot_telcell)
        self.assertEqual(
            self._step(ScreenFactory.ticket_list(card_loaded=True)), "OPEN_RECENTS"
        )
        self.assertFalse(self.env.read_config()["vm_booting"])
        self.assertEqual(self.env.read_config()["last_state"], "RESET_OPEN_RECENTS")

        # 5. Worker supersession (bumped worker_start_ms) returns ABORT_PREEMPTED;
        # cooperative in-place reset mid-sendPhoto returns CLOSE_MODAL instead.
        self.setUp()
        self._seed_active_run(step_count=1)
        cfg_ws = self.env.read_config()
        cfg_ws["worker_start_ms"] = 100
        cfg_ws["run_start_ms"] = 100
        self.env.write_config(cfg_ws)
        env_ref = self.env

        class _BumpOnPhoto(list):
            def __init__(self, initial: list, *, supersede: bool) -> None:
                super().__init__(initial)
                self.supersede = supersede
                self.done = False

            def append(self, item: dict) -> None:
                super().append(item)
                if not self.done and item.get("method") == "sendPhoto":
                    self.done = True
                    fresh = env_ref.read_config()
                    fresh["capture_mode"] = "reset"
                    fresh["run_start_ms"] = 200
                    if self.supersede:
                        fresh["worker_start_ms"] = 999
                    env_ref.write_config(fresh)

        env_ref.tg_calls = _BumpOnPhoto(env_ref.tg_calls, supersede=True)
        self.assertEqual(
            self._step(ScreenFactory.qr_modal(loaded=True)), "ABORT_PREEMPTED"
        )

        self.setUp()
        self._seed_active_run(step_count=1)
        cfg_coop = self.env.read_config()
        cfg_coop["worker_start_ms"] = 100
        cfg_coop["run_start_ms"] = 100
        self.env.write_config(cfg_coop)
        self.env.tg_calls = _BumpOnPhoto(self.env.tg_calls, supersede=False)
        env_ref = self.env
        env_ref.tg_calls = _BumpOnPhoto(env_ref.tg_calls, supersede=False)
        self.assertEqual(self._step(ScreenFactory.qr_modal(loaded=True)), "CLOSE_MODAL")
        self.assertTrue(env_ref.read_config()["qr_was_closed"])
        self.assertEqual(env_ref.read_config()["capture_mode"], "reset")


if __name__ == "__main__":
    unittest.main()
