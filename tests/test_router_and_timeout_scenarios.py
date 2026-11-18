"""Scenario tests executing the generated router & timeout BeanShell scripts."""

from __future__ import annotations

import unittest

import generate_macro as gm
from tests.bsh_runtime import MockAndroidEnv, run_bsh_script

ROUTER_SCRIPT = gm.build_router_script()
INIT_STATUS_SCRIPT = gm.build_init_status_script()
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
    callback_id: str = "",
    callback_data: str = "",
    callback_msg_id: str = "0",
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
            "callback_id": callback_id,
            "callback_data": callback_data,
            "callback_msg_id": callback_msg_id,
        },
    )


def _run_init_status(env: MockAndroidEnv) -> str:
    return run_bsh_script(INIT_STATUS_SCRIPT, env, {"bot_token": "test-token"})


def _dispatch_qr(
    env: MockAndroidEnv,
    chat_id: str,
    msg_text: str,
    update_id: str = "0",
    admin_id: str = ADMIN_ID,
    callback_id: str = "",
    callback_data: str = "",
    callback_msg_id: str = "0",
) -> str:
    res = _run_router(
        env,
        chat_id,
        msg_text,
        update_id=update_id,
        admin_id=admin_id,
        callback_id=callback_id,
        callback_data=callback_data,
        callback_msg_id=callback_msg_id,
    )
    if res == "RUN":
        _run_init_status(env)
    return res


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
        # Stale private frame from an aborted run is swept on RUN without HTTP wait
        self.env.write_text("/storage/emulated/0/komobot_ss/frame.png", "stale")
        self.assertEqual(
            _run_router(self.env, ADMIN_ID, "📸 Take QR Screenshot"), "RUN"
        )
        self.assertEqual(self.env.tg_calls, [])
        self.assertNotIn("/storage/emulated/0/komobot_ss/frame.png", self.env.files)
        self.assertEqual(_run_init_status(self.env), "SENT")
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
        self.assertEqual(_dispatch_qr(self.env, ADMIN_ID, "/qr"), "RUN")
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        cfg = self.env.read_config()
        cfg["last_state"] = "WHITE_LOADING"
        self.env.write_config(cfg)

        self.env.tg_calls.clear()
        self.env.http_connections.clear()
        self.assertEqual(_run_timeout(self.env, "WAIT"), "SCREEN_OFF")
        after_cfg = self.env.read_config()
        self.assertEqual(after_cfg["busy_until"], 0)
        self.assertEqual(after_cfg["queue"], [])
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertEqual(len(edits), 2)
        self.assertIn("last state: WHITE_LOADING", edits[0]["text"])
        self.assertIn("Previous request timed out", edits[1]["text"])
        admin_sends = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "sendMessage"
        ]
        self.assertEqual(len(admin_sends), 1)
        self.assertEqual(admin_sends[0]["chat_id"], int(ADMIN_ID))
        self.assertIn("Queued user request(s) failed", admin_sends[0]["text"])
        self.assertIn(ALLOWED_USER, admin_sends[0]["text"])
        for conn in self.env.http_connections:
            self.assertTrue(conn["stream_read"])
            self.assertTrue(conn["stream_closed"])
            self.assertFalse(conn["disconnected"])

        # Scenario 2: Admin Reset VM App + DONE_RESET
        self.env.tg_calls.clear()
        self.assertEqual(_dispatch_qr(self.env, ADMIN_ID, "🧹 Reset VM App"), "RUN")
        self.assertEqual(self.env.read_config()["capture_mode"], "reset")
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "IGNORE")
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "DONE_RESET"), "SCREEN_OFF")
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
        self.assertEqual(_run_timeout(self.env, "DONE"), "SCREEN_OFF")
        self.assertEqual(self.env.tg_calls, [])

        # Scenario 4: DONE exit after new run started skips cleanup & keeps screen on
        self.assertEqual(_dispatch_qr(self.env, ALLOWED_USER, "/qr"), "RUN")
        busy_snapshot = self.env.read_config()["busy_until"]
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "DONE"), "KEEP_ON")
        self.assertEqual(self.env.read_config()["busy_until"], busy_snapshot)
        self.assertEqual(self.env.tg_calls, [])

        # Scenario 5: DONE_RESET after reset_notified + new run also returns KEEP_ON
        new_cfg = self.env.read_config()
        new_cfg["reset_notified"] = True
        self.env.write_config(new_cfg)
        self.assertEqual(_run_timeout(self.env, "DONE_RESET"), "KEEP_ON")
        self.assertEqual(self.env.read_config()["busy_until"], busy_snapshot)

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
            _dispatch_qr(self.env, ALLOWED_USER, "📸 Take QR Screenshot"), "RUN"
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

        # Regular user timeout hides internal last_state detail, but alerts admin
        cfg = self.env.read_config()
        cfg["last_state"] = "WHITE_LOADING"
        cfg["step_count"] = 17
        self.env.write_config(cfg)
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "ABORT_TIMEOUT"), "SCREEN_OFF")
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertEqual(len(edits), 3)
        self.assertEqual(
            edits[0]["text"], "❌ Timed out generating QR code. Please try again."
        )
        self.assertNotIn("last state", edits[0]["text"])
        sends = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "sendMessage"
        ]
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]["chat_id"], int(ADMIN_ID))
        self.assertIn(f"chat_id: {ALLOWED_USER}", sends[0]["text"])
        self.assertIn("WHITE_LOADING (step 17)", sends[0]["text"])
        self.assertIn(f"Affected queued users: {THIRD_USER}", sends[0]["text"])

        # Admin RUN preserves exact original diagnostic text
        self.env.tg_calls.clear()
        self.assertEqual(_dispatch_qr(self.env, ADMIN_ID, "/qr"), "RUN")
        self.assertEqual(
            self.env.tg_calls[-1]["payload"]["text"],
            "🔍 Waking phone & checking Virtual Master...",
        )
        self.assertEqual(self.env.read_config()["progress_pct"], 0)

    def test_admin_reset_preempts_active_and_queued_requests(self) -> None:
        # Active user + queued user running QR pipeline
        self.assertEqual(_dispatch_qr(self.env, ALLOWED_USER, "/qr"), "RUN")
        self.assertEqual(_run_router(self.env, THIRD_USER, "/qr"), "IGNORE")
        active_cfg = self.env.read_config()
        old_run_start = active_cfg["run_start_ms"]
        old_user_mid = active_cfg["status_message_id"]
        queued_mid = active_cfg["queue"][0]["status_message_id"]

        # Admin Reset VM App cooperates in-place when live worker is active (IGNORE)
        self.env.tg_calls.clear()
        self.env.advance_time(500)
        self.assertEqual(_run_router(self.env, ADMIN_ID, "🧹 Reset VM App"), "IGNORE")
        pre_init_cfg = self.env.read_config()
        self.assertEqual(pre_init_cfg["capture_mode"], "reset")
        self.assertEqual(pre_init_cfg["active_chat_id"], int(ADMIN_ID))
        self.assertGreater(pre_init_cfg["busy_until"], self.env.now_ms + 50000)
        self.assertGreater(pre_init_cfg["run_start_ms"], old_run_start)
        self.assertEqual(pre_init_cfg["reset_stage"], 0)
        self.assertEqual(pre_init_cfg["reset_kills"], 0)
        self.assertTrue(pre_init_cfg["worker_active"])
        self.assertGreater(pre_init_cfg["status_message_id"], 0)
        sends = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "sendMessage"
        ]
        edits = [
            c["payload"] for c in self.env.tg_calls if c["method"] == "editMessageText"
        ]
        self.assertEqual(
            sends,
            [
                {
                    "chat_id": int(ADMIN_ID),
                    "text": "🔄 Force-restarting Telcell Wallet...",
                }
            ],
        )
        self.assertEqual(
            sorted((e["chat_id"], e["message_id"], e["text"]) for e in edits),
            sorted(
                [
                    (
                        int(ALLOWED_USER),
                        old_user_mid,
                        "❌ Request cancelled by VM reset. Please try again.",
                    ),
                    (
                        int(THIRD_USER),
                        queued_mid,
                        "❌ Request cancelled by VM reset. Please try again.",
                    ),
                ]
            ),
        )

        # Sending another Reset while reset is already running does NOT self-preempt
        self.env.advance_time(3500)
        self.assertEqual(_run_router(self.env, ADMIN_ID, "🧹 Reset VM App"), "IGNORE")
        self.assertIn("already in progress", self.env.tg_calls[-1]["payload"]["text"])

        # Dead/stalled worker fallback (>= 20s heartbeat stale) spawns fresh RUN worker
        self.env.advance_time(65000)
        self.assertEqual(_dispatch_qr(self.env, ALLOWED_USER, "/qr"), "RUN")
        stale_cfg = self.env.read_config()
        stale_cfg["worker_heartbeat_ms"] = self.env.now_ms - 25000
        self.env.write_config(stale_cfg)
        self.env.tg_calls.clear()
        self.assertEqual(_run_router(self.env, ADMIN_ID, "🧹 Reset VM App"), "RUN")
        fallback_cfg = self.env.read_config()
        self.assertEqual(len(fallback_cfg["preempted_notices"]), 1)
        self.assertEqual(_run_init_status(self.env), "SENT")
        self.assertEqual(self.env.read_config()["preempted_notices"], [])

        # Superseded stalled worker ABORT_PREEMPTED keeps screen on cleanly
        self.env.tg_calls.clear()
        before_busy = self.env.read_config()["busy_until"]
        self.assertEqual(_run_timeout(self.env, "ABORT_PREEMPTED"), "KEEP_ON")
        self.assertEqual(self.env.read_config()["busy_until"], before_busy)
        self.assertEqual(self.env.tg_calls, [])

    def test_startup_barrier_and_orphaned_init_status_cleanup(self) -> None:
        # Router RUN sets worker_pending_start_ms > 0; if init_status is in-flight
        # during sendMessage when Reset preempts, init_status deletes its orphaned bar.
        self.assertEqual(_run_router(self.env, ALLOWED_USER, "/qr"), "RUN")
        initial_cfg = self.env.read_config()
        self.assertGreater(initial_cfg["worker_pending_start_ms"], 0)

        preempted = {"done": False}
        env_ref = self.env

        class _PreemptOnSend(list):
            def append(self, item: dict) -> None:
                super().append(item)
                if not preempted["done"] and item.get("method") == "sendMessage":
                    preempted["done"] = True
                    # Simulate Reset preempting while init_status waits on sendMsg
                    _run_router(env_ref, ADMIN_ID, "🧹 Reset VM App")

        self.env.tg_calls = _PreemptOnSend()
        # Init_status clears pending flag before sendMsg, gets preempted mid-sendMsg,
        # detects lost ownership afterward, and deletes orphaned "10%" bar.
        self.assertEqual(_run_init_status(self.env), "SENT")
        methods = [c["method"] for c in self.env.tg_calls]
        self.assertIn("deleteMessage", methods)
        final_cfg = self.env.read_config()
        self.assertEqual(final_cfg["active_chat_id"], int(ADMIN_ID))
        self.assertEqual(final_cfg["capture_mode"], "reset")
        self.assertEqual(final_cfg["worker_pending_start_ms"], 0)

    def test_callback_query_refresh_qr_routing_and_ack(self) -> None:
        # 1. Idle inline "🔄 Refresh QR" callback triggers RUN and stores pending_cb_id;
        # init_status answers the callback during wake settle and clears it.
        res = _run_router(
            self.env,
            ADMIN_ID,
            msg_text="🔄 Refresh QR",
            update_id="501",
            callback_id="cb-101",
            callback_data="/qr",
        )
        self.assertEqual(res, "RUN")
        cfg = self.env.read_config()
        self.assertEqual(cfg["last_update_id"], 501)
        self.assertEqual(cfg["last_msg_text"], "/qr")
        self.assertEqual(cfg["pending_cb_id"], "cb-101")
        self.assertEqual(cfg["pending_delete_cid"], 0)
        self.assertEqual(cfg["pending_delete_mid"], 0)
        self.assertFalse(cfg["vm_seen"])
        self.assertFalse(cfg["vm_launched"])
        self.assertEqual(self.env.tg_calls, [])

        self.assertEqual(_run_init_status(self.env), "SENT")
        methods = [c["method"] for c in self.env.tg_calls]
        self.assertEqual(methods, ["answerCallbackQuery", "sendMessage"])
        self.assertEqual(
            self.env.tg_calls[0]["payload"], {"callback_query_id": "cb-101"}
        )
        self.assertEqual(self.env.read_config()["pending_cb_id"], "")

        # 2. Duplicate callback tap by active user <3s still answers callback query
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ADMIN_ID,
                msg_text="🔄 Refresh QR",
                update_id="502",
                callback_id="cb-102",
                callback_data="/qr",
            ),
            "IGNORE",
        )
        self.assertEqual(
            self.env.tg_calls,
            [
                {
                    "method": "answerCallbackQuery",
                    "status": 200,
                    "payload": {"callback_query_id": "cb-102"},
                }
            ],
        )

        # 3. Queued user callback answers callback AND sends progress queue bar
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ALLOWED_USER,
                msg_text="🔄 Refresh QR",
                update_id="503",
                callback_id="cb-103",
                callback_data="/qr",
            ),
            "IGNORE",
        )
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["answerCallbackQuery", "sendMessage"],
        )
        self.assertEqual(
            self.env.tg_calls[0]["payload"], {"callback_query_id": "cb-103"}
        )

        # 4. Unauthorized callback answers callback AND sends unauthorized error
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                UNKNOWN_USER,
                msg_text="",
                update_id="504",
                callback_id="cb-104",
                callback_data="/qr",
            ),
            "IGNORE",
        )
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["answerCallbackQuery", "sendMessage"],
        )
        self.assertIn("Unauthorized", self.env.tg_calls[1]["payload"]["text"])

        # 5. Duplicate update_id skips all HTTP calls
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ADMIN_ID,
                msg_text="",
                update_id="504",
                callback_id="cb-105",
                callback_data="/qr",
            ),
            "IGNORE",
        )
        self.assertEqual(self.env.tg_calls, [])

    def test_in_place_refresh_button_progress_noop_and_timeout(self) -> None:
        # 1. Idle callback with message_id edits inline button to 10% noop bar
        res = _run_router(
            self.env,
            ADMIN_ID,
            msg_text="🔄 Refresh QR",
            update_id="601",
            callback_id="cb-201",
            callback_data="/qr",
            callback_msg_id="777",
        )
        self.assertEqual(res, "RUN")
        cfg = self.env.read_config()
        self.assertTrue(cfg["status_is_media"])
        self.assertTrue(cfg["media_init_pending"])
        self.assertEqual(cfg["status_message_id"], 777)
        self.assertEqual(cfg["pending_cb_id"], "cb-201")
        self.assertEqual(cfg["progress_pct"], 10)
        self.assertEqual(self.env.tg_calls, [])

        self.assertEqual(_run_init_status(self.env), "SENT")
        # Button flips to the progress bar first, then the callback spinner clears
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["editMessageReplyMarkup", "answerCallbackQuery"],
        )
        self.assertEqual(
            self.env.tg_calls[1]["payload"], {"callback_query_id": "cb-201"}
        )
        btn = self.env.tg_calls[0]["payload"]["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(btn["text"], "⏳ 🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%")
        self.assertEqual(btn["callback_data"], "noop")
        self.assertEqual(self.env.tg_calls[0]["payload"]["message_id"], 777)
        after_init = self.env.read_config()
        self.assertFalse(after_init["media_init_pending"])
        self.assertEqual(after_init["pending_cb_id"], "")

        # 2. Tapping the progress button itself (callback_data="noop") shows toast only
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ADMIN_ID,
                msg_text="",
                update_id="602",
                callback_id="cb-202",
                callback_data="noop",
                callback_msg_id="777",
            ),
            "IGNORE",
        )
        self.assertEqual(
            self.env.tg_calls,
            [
                {
                    "method": "answerCallbackQuery",
                    "status": 200,
                    "payload": {
                        "callback_query_id": "cb-202",
                        "text": "⏳ Refresh already in progress...",
                    },
                }
            ],
        )

        # 3. Same active user tapping >=3s later gets busy toast without chat spam
        self.env.advance_time(3500)
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ADMIN_ID,
                msg_text="🔄 Refresh QR",
                update_id="603",
                callback_id="cb-203",
                callback_data="/qr",
                callback_msg_id="777",
            ),
            "IGNORE",
        )
        self.assertEqual(
            self.env.tg_calls,
            [
                {
                    "method": "answerCallbackQuery",
                    "status": 200,
                    "payload": {
                        "callback_query_id": "cb-203",
                        "text": "⏳ Your request is already in progress.",
                    },
                }
            ],
        )

        # 4. Queued user tapping Refresh QR edits their button to queued status;
        # repeat tap shows toast
        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ALLOWED_USER,
                msg_text="🔄 Refresh QR",
                update_id="604",
                callback_id="cb-204",
                callback_data="/qr",
                callback_msg_id="888",
            ),
            "IGNORE",
        )
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["answerCallbackQuery", "editMessageReplyMarkup"],
        )
        q_btn = self.env.tg_calls[1]["payload"]["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(q_btn["text"], "⏳ Queued (#1)...")
        self.assertEqual(q_btn["callback_data"], "noop")
        q_cfg = self.env.read_config()
        self.assertEqual(
            q_cfg["queue"],
            [
                {
                    "chat_id": int(ALLOWED_USER),
                    "status_message_id": 888,
                    "status_is_media": True,
                }
            ],
        )

        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env,
                ALLOWED_USER,
                msg_text="🔄 Refresh QR",
                update_id="605",
                callback_id="cb-205",
                callback_data="/qr",
                callback_msg_id="888",
            ),
            "IGNORE",
        )
        self.assertEqual(
            self.env.tg_calls,
            [
                {
                    "method": "answerCallbackQuery",
                    "status": 200,
                    "payload": {
                        "callback_query_id": "cb-205",
                        "text": "⏳ You are already in the queue (#1).",
                    },
                }
            ],
        )

        # 5. Timeout restores retry buttons via editMessageReplyMarkup (never
        # editMessageText) and alerts Admin about affected queued regular users
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "ABORT_TIMEOUT"), "SCREEN_OFF")
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["editMessageReplyMarkup", "editMessageReplyMarkup", "sendMessage"],
        )
        for call, expected_cid, expected_mid in zip(
            self.env.tg_calls[:2], [int(ADMIN_ID), int(ALLOWED_USER)], [777, 888]
        ):
            self.assertEqual(call["payload"]["chat_id"], expected_cid)
            self.assertEqual(call["payload"]["message_id"], expected_mid)
            retry_btn = call["payload"]["reply_markup"]["inline_keyboard"][0][0]
            self.assertEqual(retry_btn["text"], "❌ Timed out • 🔄 Retry")
            self.assertEqual(retry_btn["callback_data"], "/qr")
        self.assertEqual(self.env.tg_calls[2]["payload"]["chat_id"], int(ADMIN_ID))
        self.assertIn(ALLOWED_USER, self.env.tg_calls[2]["payload"]["text"])
        end_cfg = self.env.read_config()
        self.assertFalse(end_cfg["status_is_media"])
        self.assertFalse(end_cfg["media_init_pending"])
        self.assertEqual(end_cfg["queue"], [])

    def test_in_place_refresh_admin_reset_preemption_restores_retry_button(
        self,
    ) -> None:
        # 1. Cold-path preemption (no live worker thread) defers notice to InitStatus
        self.assertEqual(
            _run_router(
                self.env,
                ALLOWED_USER,
                msg_text="🔄 Refresh QR",
                update_id="701",
                callback_id="cb-301",
                callback_data="/qr",
                callback_msg_id="901",
            ),
            "RUN",
        )
        stale_cfg = self.env.read_config()
        stale_cfg["worker_active"] = False
        stale_cfg["worker_pending_start_ms"] = 0
        self.env.write_config(stale_cfg)
        self.assertEqual(
            _run_router(
                self.env, ADMIN_ID, msg_text="🧹 Reset VM App", update_id="702"
            ),
            "RUN",
        )
        self.env.tg_calls.clear()
        self.assertEqual(_run_init_status(self.env), "SENT")
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["sendMessage", "editMessageReplyMarkup"],
        )
        self.assertEqual(self.env.tg_calls[1]["payload"]["message_id"], 901)
        self.assertEqual(
            self.env.tg_calls[1]["payload"]["reply_markup"]["inline_keyboard"][0][0],
            {"text": "❌ Cancelled • 🔄 Retry", "callback_data": "/qr"},
        )
        self.env.tg_calls.clear()
        self.assertEqual(_run_timeout(self.env, "DONE_RESET"), "SCREEN_OFF")
        self.assertIn("VM app reset complete", self.env.tg_calls[-1]["payload"]["text"])

        # 2. Cooperative preemption while worker is already active
        self.env.tg_calls.clear()
        self.assertEqual(
            _dispatch_qr(
                self.env,
                ALLOWED_USER,
                msg_text="🔄 Refresh QR",
                update_id="703",
                callback_id="cb-302",
                callback_data="/qr",
                callback_msg_id="902",
            ),
            "RUN",
        )
        self.assertEqual(
            _run_router(
                self.env,
                THIRD_USER,
                msg_text="🔄 Refresh QR",
                update_id="704",
                callback_id="cb-303",
                callback_data="/qr",
                callback_msg_id="903",
            ),
            "IGNORE",
        )

        self.env.tg_calls.clear()
        self.assertEqual(
            _run_router(
                self.env, ADMIN_ID, msg_text="🧹 Reset VM App", update_id="705"
            ),
            "IGNORE",
        )
        self.assertEqual(
            [c["method"] for c in self.env.tg_calls],
            ["sendMessage", "editMessageReplyMarkup", "editMessageReplyMarkup"],
        )
        self.assertEqual(self.env.tg_calls[1]["payload"]["message_id"], 902)
        self.assertEqual(self.env.tg_calls[2]["payload"]["message_id"], 903)
        for c in self.env.tg_calls[1:]:
            self.assertEqual(
                c["payload"]["reply_markup"]["inline_keyboard"][0][0],
                {"text": "❌ Cancelled • 🔄 Retry", "callback_data": "/qr"},
            )


if __name__ == "__main__":
    unittest.main()
