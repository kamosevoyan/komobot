"""Scenario tests executing the generated router & timeout BeanShell scripts."""

from __future__ import annotations

import unittest

import generate_macro as gm
from tests.bsh_runtime import MockAndroidEnv, run_bsh_script

ROUTER_SCRIPT = gm.build_router_script()
TIMEOUT_SCRIPT = gm.build_timeout_script()
ADMIN_ID = "111222333"
ALLOWED_USER = "222333444"
THIRD_USER = "555666777"
UNKNOWN_USER = "123450000"


def _run_router(
    env: MockAndroidEnv,
    chat_id: str,
    msg_text: str,
    update_id: str = "0",
    admin_id: str = ADMIN_ID,
) -> str:
    return run_bsh_script(
        ROUTER_SCRIPT,
        env,
        {
            "bot_token": "test-token",
            "app_name": "ru.deltapay.puntopago.telcell",
            "admin_id": admin_id,
            "chat_id": chat_id,
            "update_id": update_id,
            "msg_text": msg_text,
        },
    )


def _run_timeout(env: MockAndroidEnv, step_cmd: str) -> str:
    return run_bsh_script(
        TIMEOUT_SCRIPT, env, {"bot_token": "test-token", "step_cmd": step_cmd}
    )


class TestRouterAndTimeoutScenarios(unittest.TestCase):
    """End-to-end router, auth, queue, and post-loop guard scenarios."""

    def setUp(self) -> None:
        self.env = MockAndroidEnv(now_ms=1794735000000)
        self.env.write_config(
            {
                "admin_id": int(ADMIN_ID),
                "allowed_users": [int(ADMIN_ID), int(ALLOWED_USER), int(THIRD_USER)],
                "public_access": True,
                "busy_until": 0,
                "last_update_id": 500,
            }
        )

    def test_deduplication_and_synthetic_zero_update_id(self) -> None:
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "/qr", update_id="500"), "IGNORE"
        )
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "/qr", update_id="499"), "IGNORE"
        )
        self.assertEqual(self.env.tg_calls, [])
        self.assertEqual(self.env.read_config()["last_update_id"], 500)

        # update_id == "0" bypasses dedup and never advances last_update_id
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "📸 Take QR Screenshot", update_id="0"),
            "RUN",
        )
        cfg = self.env.read_config()
        self.assertEqual(cfg["last_update_id"], 500)
        self.assertEqual(cfg["last_msg_text"], "📸 Take QR Screenshot")

        # Simulate idle again and check higher non-zero update_id advances counter
        cfg["busy_until"] = 0
        self.env.write_config(cfg)
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr", update_id="501"), "RUN")
        self.assertEqual(self.env.read_config()["last_update_id"], 501)

        # Invalid/zero chat_id safely ignored
        self.assertEqual(_run_router(self.env, "0", "/qr", update_id="502"), "IGNORE")
        self.assertEqual(_run_router(self.env, "abc", "/qr", update_id="503"), "IGNORE")

    def test_auth_public_lock_and_start_keyboards(self) -> None:
        self.assertEqual(_run_router(self.env, UNKNOWN_USER, "/qr"), "IGNORE")
        self.assertEqual(len(self.env.tg_calls), 1)
        self.assertIn("Unauthorized", self.env.tg_calls[0]["payload"]["text"])

        # Admin /start includes Reset VM App keyboard button; regular user does not
        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/start"), "IGNORE")
        admin_kb = self.env.tg_calls[0]["payload"]["reply_markup"]["keyboard"]
        self.assertIn("🧹 Reset VM App", [b for row in admin_kb for b in row])

        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/start"), "IGNORE")
        user_kb = self.env.tg_calls[0]["payload"]["reply_markup"]["keyboard"]
        self.assertEqual(user_kb, [["📸 Take QR Screenshot"]])

        # Locking public access blocks non-admin users while keeping admin active
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "🛑 Toggle Public Access"), "IGNORE"
        )
        self.assertFalse(self.env.read_config()["public_access"])
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        self.assertIn("locked by the admin", self.env.tg_calls[-1]["payload"]["text"])
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "RUN")

    def test_admin_user_management_commands(self) -> None:
        new_id = 444555666
        # Non-admin cannot invoke admin user commands
        self.assertEqual(
            _run_router(self.env, ALLOWED_USER, f"/adduser {new_id}"), "IGNORE"
        )
        self.assertNotIn(new_id, self.env.read_config()["allowed_users"])

        # Admin adds, deduplicates, lists, and removes user
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, f"/adduser {new_id}"), "IGNORE"
        )
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, f"/adduser {new_id}"), "IGNORE"
        )
        allowed = self.env.read_config()["allowed_users"]
        self.assertEqual(allowed.count(new_id), 1)

        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ADMIN_ID, "👥 List Users"), "IGNORE")
        self.assertIn(str(new_id), self.env.tg_calls[-1]["payload"]["text"])

        self.assertEqual(
            _run_router(self.env, ADMIN_ID, f"/removeuser {new_id}"), "IGNORE"
        )
        self.assertNotIn(new_id, self.env.read_config()["allowed_users"])

        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, f"/removeuser {new_id}"), "IGNORE"
        )
        self.assertIn(
            "not in the allowed list", self.env.tg_calls[-1]["payload"]["text"]
        )

    def test_busy_lease_same_user_and_multi_user_fifo_queue(self) -> None:
        start_ms = self.env.now_ms
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "📸 Take QR Screenshot"), "RUN"
        )
        cfg = self.env.read_config()
        self.assertEqual(cfg["busy_until"], start_ms + 45000)
        self.assertEqual(cfg["active_chat_id"], int(ADMIN_ID))
        self.assertEqual(cfg["capture_mode"], "qr")
        self.assertEqual(cfg["white_count"], 0)
        self.assertEqual(cfg["loading_count"], 0)
        self.assertEqual(cfg["other_count"], 0)
        self.assertEqual(cfg["last_state"], "INIT")
        self.assertGreater(cfg["status_message_id"], 0)

        # Same active user within 3s is ignored silently; after 3s gets progress note
        calls_before = len(self.env.tg_calls)
        self.env.advance_time(1500)
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "IGNORE")
        self.assertEqual(len(self.env.tg_calls), calls_before)

        self.env.advance_time(2000)
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "IGNORE")
        self.assertIn("already in progress", self.env.tg_calls[-1]["payload"]["text"])

        # Another allowed user is queued and extends busy_until by +30s
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        cfg = self.env.read_config()
        self.assertEqual(cfg["busy_until"], start_ms + 75000)
        self.assertEqual(len(cfg["queue"]), 1)
        self.assertEqual(cfg["queue"][0]["chat_id"], int(ALLOWED_USER))
        self.assertGreater(cfg["queue"][0]["status_message_id"], 0)

        # Duplicate request from queued user notifies position without re-adding
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        self.assertIn(
            "already in the queue (#1)", self.env.tg_calls[-1]["payload"]["text"]
        )
        self.assertEqual(len(self.env.read_config()["queue"]), 1)

        # Third user enters queue at #2
        self.assertEqual(_run_router(self.env, THIRD_USER, "/qr"), "IGNORE")
        self.assertEqual(len(self.env.read_config()["queue"]), 2)
        self.assertIn("Queued (#2)", self.env.tg_calls[-1]["payload"]["text"])

    def test_post_loop_timeout_guard_and_reset_cleanup(self) -> None:
        # Scenario 1: loop exhausted while still busy on WHITE_LOADING with queued user
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "RUN")
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        cfg = self.env.read_config()
        cfg["last_state"] = "WHITE_LOADING"
        self.env.write_config(cfg)

        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "WAIT"), "OK")
        after_cfg = self.env.read_config()
        self.assertEqual(after_cfg["busy_until"], 0)
        self.assertEqual(after_cfg["queue"], [])
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertEqual(len(edits), 2)
        self.assertIn("last state: WHITE_LOADING", edits[0]["text"])
        self.assertIn("Previous request timed out", edits[1]["text"])

        # Scenario 2: Admin Reset VM App + DONE_RESET
        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ADMIN_ID, "🧹 Reset VM App"), "RUN")
        self.assertEqual(self.env.read_config()["capture_mode"], "reset")
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "DONE_RESET"), "OK")
        self.assertEqual(self.env.read_config()["busy_until"], 0)
        self.assertEqual(self.env.read_config()["queue"], [])
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertIn("VM app reset complete", edits[0]["text"])
        self.assertIn("cancelled by VM reset", edits[1]["text"])

        # Scenario 3: Clean DONE exit leaves timeout guard as no-op
        cfg = self.env.read_config()
        cfg["busy_until"] = 0
        self.env.write_config(cfg)
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "DONE"), "OK")
        self.assertEqual(self.env.tg_calls, [])

    def test_long_inactivity_expired_lease_recovery(self) -> None:
        # Simulate hours of inactivity after an interrupted prior run that left
        # an expired busy_until lease and stale queue/recovery counters on disk.
        self.env.advance_time(6 * 3600 * 1000)
        cfg = self.env.read_config()
        cfg.update(
            {
                "busy_until": self.env.now_ms - 6 * 3600 * 1000,
                "active_chat_id": int(THIRD_USER),
                "status_message_id": 77,
                "capture_mode": "qr",
                "queue": [{"chat_id": int(THIRD_USER), "status_message_id": 78}],
                "qr_was_closed": True,
                "step_count": 19,
                "white_count": 4,
                "loading_count": 5,
                "other_count": 2,
                "last_state": "WHITE_LOADING",
                "last_update_id": 500,
            }
        )
        self.env.write_config(cfg)

        self.assertEqual(
            _run_router(
                self.env, ALLOWED_USER, "📸 Take QR Screenshot", update_id="501"
            ),
            "RUN",
        )
        fresh = self.env.read_config()
        self.assertEqual(fresh["active_chat_id"], int(ALLOWED_USER))
        self.assertEqual(fresh["busy_until"], self.env.now_ms + 45000)
        self.assertEqual(fresh["queue"], [])
        self.assertFalse(fresh["qr_was_closed"])
        self.assertEqual(fresh["step_count"], 0)
        self.assertEqual(fresh["white_count"], 0)
        self.assertEqual(fresh["loading_count"], 0)
        self.assertEqual(fresh["other_count"], 0)
        self.assertEqual(fresh["last_state"], "INIT")
        self.assertEqual(fresh["last_update_id"], 501)

    def test_regular_user_progress_bar_vs_admin_detailed_logging(self) -> None:
        # Regular user RUN shows 10% progress bar instead of internal step logs
        self.assertEqual(
            _run_router(self.env, ALLOWED_USER, "📸 Take QR Screenshot"), "RUN"
        )
        run_msg = self.env.tg_calls[-1]["payload"]["text"]
        self.assertEqual(run_msg, "⏳ Generating QR code...\n🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%")
        self.assertEqual(self.env.read_config()["progress_pct"], 10)

        # Queued regular user gets 0% progress bar; queued admin keeps detailed text
        self.assertEqual(_run_router(self.env, THIRD_USER, "/qr"), "IGNORE")
        self.assertEqual(
            self.env.tg_calls[-1]["payload"]["text"],
            "⏳ Queued (#1)...\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%",
        )
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "IGNORE")
        self.assertEqual(
            self.env.tg_calls[-1]["payload"]["text"],
            "⏳ Queued (#2) — waiting for current request to finish...",
        )

        # Regular user timeout hides internal last_state detail
        cfg = self.env.read_config()
        cfg["last_state"] = "WHITE_LOADING"
        self.env.write_config(cfg)
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "WAIT"), "OK")
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertEqual(len(edits), 3)
        self.assertEqual(
            edits[0]["text"], "❌ Timed out generating QR code. Please try again."
        )
        self.assertNotIn("last state", edits[0]["text"])

        # Admin RUN preserves exact original diagnostic text
        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ADMIN_ID, "/qr"), "RUN")
        self.assertEqual(
            self.env.tg_calls[-1]["payload"]["text"],
            "🔍 Waking phone & checking Virtual Master...",
        )
        self.assertEqual(self.env.read_config()["progress_pct"], 0)


if __name__ == "__main__":
    unittest.main()
