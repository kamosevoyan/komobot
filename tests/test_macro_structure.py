"""Offline structural, regex, keypad, and BeanShell hygiene tests."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import generate_macro as gm
from tests.bsh_runtime import compile_bsh_to_python


def _iter_actions_and_constraints(actions: list[dict]):
    for action in actions:
        yield action
        for constraint in action.get("m_constraintList", []):
            yield constraint


def _find_cmd_branch(actions: list[dict], cmd: str) -> list[dict]:
    """Return actions inside the ``IfConditionAction(step_cmd == cmd)`` branch."""
    for i, action in enumerate(actions):
        if action.get("m_classType") != "IfConditionAction":
            continue
        constraints = action.get("m_constraintList", [])
        if not constraints:
            continue
        c0 = constraints[0]
        var = c0.get("m_variable", {})
        if var.get("m_name") == "step_cmd" and c0.get("m_stringValue") == cmd:
            depth = 1
            branch: list[dict] = []
            for j in range(i + 1, len(actions)):
                ct = actions[j].get("m_classType")
                if ct == "IfConditionAction":
                    depth += 1
                elif ct == "EndIfAction":
                    depth -= 1
                    if depth == 0:
                        return branch
                branch.append(actions[j])
    raise AssertionError(f"Branch for step_cmd={cmd!r} not found")


class TestMacroStructure(unittest.TestCase):
    """Validate Komobot macro JSON schema, control flow, regexes, and PIN mapping."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.macro_doc = gm.build_macro(
            bot_token_var="12345:TEST_TOKEN",
            admin_id_var="999999999",
            app_pin_var="1234",
            app_name_var="ru.deltapay.puntopago.telcell",
        )
        cls.macro = cls.macro_doc["macro"]
        cls.actions = cls.macro["m_actionList"]

    def test_macro_metadata_and_webhook_trigger(self) -> None:
        self.assertEqual(self.macro_doc["macroExportVersion"], 1)
        self.assertEqual(self.macro["m_name"], "Komobot Controller")
        self.assertTrue(self.macro["m_enabled"])
        triggers = self.macro["m_triggerList"]
        self.assertEqual(len(triggers), 2)
        self.assertEqual(triggers[0]["m_classType"], "WebHookTrigger")
        self.assertEqual(triggers[0]["identifier"], "komobotv2")
        self.assertEqual(triggers[0]["saveBodyVariableName"], "webhook_body")
        self.assertEqual(triggers[1]["m_classType"], "WebHookTrigger")
        self.assertEqual(triggers[1]["identifier"], "komobotv2_admin")
        self.assertEqual(triggers[1]["saveBodyVariableName"], "admin_webhook_body")

    def test_unique_negative_siguids_and_defined_local_vars(self) -> None:
        seen_ids: set[int] = set()
        for item in _iter_actions_and_constraints(self.actions):
            sid = item["m_SIGUID"]
            self.assertIsInstance(sid, int)
            self.assertLess(sid, 0)
            self.assertNotIn(sid, seen_ids, f"Duplicate m_SIGUID: {sid}")
            seen_ids.add(sid)

        declared_vars = {v["m_name"] for v in self.macro["localVariables"]}
        expected_vars = {
            "admin_bot_token",
            "admin_id",
            "admin_webhook_body",
            "app_name",
            "app_pin",
            "bot_action",
            "bot_role",
            "bot_token",
            "callback_data",
            "callback_id",
            "callback_msg_id",
            "chat_id",
            "forward_user_id",
            "msg_text",
            "screen_action",
            "sender_name",
            "sender_username",
            "step_cmd",
            "update_id",
            "webhook_body",
        }
        self.assertTrue(expected_vars.issubset(declared_vars))

        lv_re = re.compile(r"\{lv=([A-Za-z0-9_]+)\}")
        for action in self.actions:
            for field_name in ("scriptText", "m_text"):
                val = action.get(field_name, "")
                for ref in lv_re.findall(val):
                    self.assertIn(ref, declared_vars)

    def test_balanced_control_flow_and_step_cmd_coverage(self) -> None:
        if_depth = 0
        loop_depth = 0
        loop_counts: list[int] = []
        for action in self.actions:
            ct = action.get("m_classType")
            if ct == "IfConditionAction":
                if_depth += 1
            elif ct == "EndIfAction":
                if_depth -= 1
                self.assertGreaterEqual(if_depth, 0)
            elif ct == "LoopAction":
                loop_depth += 1
                loop_counts.append(action["m_fixedOptionCount"])
            elif ct == "EndLoopAction":
                loop_depth -= 1
                self.assertGreaterEqual(loop_depth, 0)
            elif ct == "BreakFromLoopAction":
                self.assertGreater(loop_depth, 0)
        self.assertEqual(if_depth, 0)
        self.assertEqual(loop_depth, 0)
        self.assertEqual(loop_counts, [130])

        # Stage 3 wakes directly onto running VM and overlaps initial Telegram status
        loop_idx = next(
            i
            for i, a in enumerate(self.actions)
            if a.get("m_classType") == "LoopAction"
        )
        end_loop_idx = next(
            i
            for i, a in enumerate(self.actions)
            if a.get("m_classType") == "EndLoopAction"
        )
        stage3 = self.actions[:loop_idx][-5:]
        stage3_types = [a.get("m_classType") for a in stage3]
        self.assertEqual(
            stage3_types,
            [
                "SystemSettingAction",
                "SystemSettingAction",
                "PauseAction",
                "ScreenOnAction",
                "JavaAction",
            ],
        )
        for act, key in zip(stage3[:2], ("screen_off_pocket", "surface_palm_touch")):
            self.assertEqual(act["settingString"], key)
            self.assertEqual(act["tableOption"], 0)
            self.assertEqual(act["valueType"], 0)
            self.assertEqual(act["valueString"], "0")
            self.assertTrue(act["useHelper"])
        self.assertEqual(stage3[2]["m_delayInMilliSeconds"], 200)
        self.assertNotIn(
            "LaunchActivityAction",
            [a.get("m_classType") for a in self.actions[:loop_idx]],
        )
        launch_vm = _find_cmd_branch(self.actions, "LAUNCH_VM")
        self.assertEqual(
            [a.get("m_classType") for a in launch_vm], ["LaunchActivityAction"]
        )
        self.assertEqual(
            launch_vm[0]["m_packageToLaunch"], "com.clone.android.dual.space"
        )
        loop_body = self.actions[loop_idx + 1 : end_loop_idx]
        self.assertNotIn("ScreenOnAction", [a.get("m_classType") for a in loop_body])
        self.assertEqual(loop_body[-1].get("m_classType"), "JavaAction")
        screenshots = [
            a for a in loop_body if a.get("m_classType") == "TakeScreenshotAction"
        ]
        self.assertEqual(len(screenshots), 1)
        ss = screenshots[0]
        self.assertEqual(ss["uiOption"], 1)
        self.assertEqual(ss["screenshotFormat"], 1)
        self.assertTrue(ss["useCustomSaveLocation"])
        self.assertEqual(ss["customAllFilesPath"], gm.SCREENSHOT_DIR)
        self.assertTrue(ss["useCustomFilename"])
        self.assertEqual(ss["customFilename"], gm.SCREENSHOT_FILE_BASE)

        returned_cmds = set(
            re.findall(r'return\s+"([A-Z0-9_]+)"\s*;', gm.build_vision_script())
        )
        self.assertTrue(returned_cmds)
        # WAIT is a pure no-op: the PostStep script provides its settle delay.
        with self.assertRaises(AssertionError):
            _find_cmd_branch(self.actions, "WAIT")
        for cmd in returned_cmds - {"WAIT"}:
            branch = _find_cmd_branch(self.actions, cmd)
            self.assertGreater(len(branch), 0, f"Empty branch for {cmd}")

    def test_enter_pin_digits_pauses_and_centered_nav_coords(self) -> None:
        # PIN entry runs via Guest ADB/u2 inside build_vision_script(), eliminating
        # the old 127-action MacroDroid ENTER_PIN tree and shrinking macro JSON ~50%.
        with self.assertRaises(AssertionError):
            _find_cmd_branch(self.actions, "ENTER_PIN")
        self.assertLess(len(self.actions), 120)
        vision_src = gm.build_vision_script()
        for x, y in gm.PIN_COORDS.values():
            self.assertIn(str(x), vision_src)
            self.assertIn(str(y), vision_src)

        def xy_points(cmd: str) -> list[tuple[int, int]]:
            return [
                (
                    a["uiInteractionConfiguration"]["xyPoint"]["x"],
                    a["uiInteractionConfiguration"]["xyPoint"]["y"],
                )
                for a in _find_cmd_branch(self.actions, cmd)
                if a.get("m_classType") == "UIInteractionAction"
            ]

        self.assertEqual(xy_points("DONE"), [(626, 121)])
        self.assertEqual(xy_points("DONE_RESET"), [])
        self.assertEqual(xy_points("ABORT_PREEMPTED"), [])
        self.assertEqual(xy_points("ABORT_TIMEOUT"), [])
        self.assertEqual(xy_points("OPEN_RECENTS"), [(567, 1553)])
        self.assertEqual(xy_points("CLICK_BACK"), [(151, 1553)])
        self.assertEqual(xy_points("RESET_TO_HOME"), [(360, 1553)])

        for break_cmd in ("DONE_RESET", "ABORT_PREEMPTED", "ABORT_TIMEOUT"):
            classes = [
                a["m_classType"] for a in _find_cmd_branch(self.actions, break_cmd)
            ]
            self.assertEqual(classes, ["BreakFromLoopAction"])

        swipe_actions = [
            a
            for a in _find_cmd_branch(self.actions, "SWIPE_KILL_RECENT")
            if a.get("m_classType") == "UIInteractionAction"
        ]
        self.assertEqual(len(swipe_actions), 1)
        swipe_cfg = swipe_actions[0]["uiInteractionConfiguration"]
        self.assertEqual(swipe_cfg["type"], "Gesture")
        self.assertEqual(
            (
                swipe_cfg["startX"],
                swipe_cfg["startY"],
                swipe_cfg["endX"],
                swipe_cfg["endY"],
                swipe_cfg["durationMs"],
                swipe_cfg["additionalFingers"],
                swipe_cfg["xyPercentages"],
                swipe_cfg["waitBeforeNext"],
            ),
            (360, 900, 360, 200, 200, 0, False, True),
        )

        # Post-loop ScreenOff & pocket/palm restore must be gated by Stage 5
        # screen_action == "SCREEN_OFF"
        timeout_action = self.actions[-7]
        screen_off_if = self.actions[-6]
        screen_off = self.actions[-5]
        restore_pocket = self.actions[-4]
        restore_palm = self.actions[-3]
        self.assertEqual(timeout_action["m_classType"], "JavaAction")
        self.assertEqual(timeout_action["responseVariableName"], "screen_action")
        self.assertEqual(screen_off_if["m_classType"], "IfConditionAction")
        c = screen_off_if["m_constraintList"][0]
        self.assertEqual(c["m_variable"]["m_name"], "screen_action")
        self.assertTrue(c["m_stringEqual"])
        self.assertEqual(c["m_stringValue"], "SCREEN_OFF")
        self.assertEqual(screen_off["m_classType"], "ScreenOnAction")
        self.assertTrue(screen_off["m_screenOff"])
        for act, key in (
            (restore_pocket, "screen_off_pocket"),
            (restore_palm, "surface_palm_touch"),
        ):
            self.assertEqual(act["m_classType"], "SystemSettingAction")
            self.assertEqual(act["settingString"], key)
            self.assertEqual(act["tableOption"], 0)
            self.assertEqual(act["valueType"], 0)
            self.assertEqual(act["valueString"], "1")
            self.assertTrue(act["useHelper"])

    def test_stage1_webhook_regex_extractors(self) -> None:
        extractors: dict[str, tuple[str, str]] = {}
        for action in self.actions[6:15]:
            self.assertEqual(action["m_classType"], "TextManipulationAction")
            suffix = action["m_text"].split("{lv=webhook_body}", 1)[1]
            regex = action["m_textManipulation"]["params"][0]
            extractors[action["variableName"]] = (regex, suffix)

        def extract(body: str) -> dict[str, str]:
            out: dict[str, str] = {}
            for name, (regex, suffix) in extractors.items():
                m = re.search(regex, body + suffix)
                self.assertIsNotNone(m, f"Extractor {name} failed on {body!r}")
                out[name] = m.group(1)
            return out

        standard = json.dumps(
            {
                "update_id": 100001,
                "message": {
                    "message_id": 42,
                    "from": {
                        "id": 111222333,
                        "is_bot": False,
                        "first_name": "Kamo",
                        "username": "kamo_s",
                    },
                    "chat": {"id": 111222333},
                    "text": "📸 Take QR Screenshot",
                },
            },
            ensure_ascii=False,
        )
        self.assertEqual(
            extract(standard),
            {
                "update_id": "100001",
                "chat_id": "111222333",
                "msg_text": "📸 Take QR Screenshot",
                "callback_id": "",
                "callback_data": "",
                "callback_msg_id": "42",
                "sender_name": "Kamo",
                "sender_username": "kamo_s",
                "forward_user_id": "0",
            },
        )

        group_msg = (
            '{"update_id":0,"message":{"chat":{"id": -100123456},"text": "/qr"}}'
        )
        self.assertEqual(
            extract(group_msg),
            {
                "update_id": "0",
                "chat_id": "-100123456",
                "msg_text": "/qr",
                "callback_id": "",
                "callback_data": "",
                "callback_msg_id": "0",
                "sender_name": "",
                "sender_username": "",
                "forward_user_id": "0",
            },
        )

        non_text_update = '{"update_id":99,"message":{"chat":{"id":77},"photo":[]}}'
        self.assertEqual(
            extract(non_text_update),
            {
                "update_id": "99",
                "chat_id": "77",
                "msg_text": "",
                "callback_id": "",
                "callback_data": "",
                "callback_msg_id": "0",
                "sender_name": "",
                "sender_username": "",
                "forward_user_id": "0",
            },
        )

        callback_update = json.dumps(
            {
                "update_id": 100002,
                "callback_query": {
                    "id": "998877665544332211",
                    "from": {"id": 111222333, "is_bot": False},
                    "message": {
                        "message_id": 505,
                        "chat": {"id": 111222333},
                        "reply_markup": {
                            "inline_keyboard": [
                                [{"text": "🔄 Refresh QR", "callback_data": "/qr"}]
                            ]
                        },
                    },
                    "chat_instance": "-1234567890",
                    "data": "/qr",
                },
            },
            ensure_ascii=False,
        )
        self.assertEqual(
            extract(callback_update),
            {
                "update_id": "100002",
                "chat_id": "111222333",
                "msg_text": "🔄 Refresh QR",
                "callback_id": "998877665544332211",
                "callback_data": "/qr",
                "callback_msg_id": "505",
                "sender_name": "",
                "sender_username": "",
                "forward_user_id": "0",
            },
        )

        # Bot inline-keyboard message before forwarded sender_user skips bot name
        bot_msg_with_forward = json.dumps(
            {
                "update_id": 100003,
                "message": {
                    "message_id": 600,
                    "from": {"id": 999, "is_bot": True, "first_name": "Komobot"},
                    "forward_origin": {
                        "type": "user",
                        "sender_user": {"id": 444555666, "first_name": "Eve"},
                    },
                    "chat": {"id": 111222333},
                    "text": "hi",
                },
            },
            ensure_ascii=False,
        )
        res_fwd = extract(bot_msg_with_forward)
        self.assertEqual(res_fwd["sender_name"], "")
        self.assertEqual(res_fwd["forward_user_id"], "444555666")

        self.assertEqual(
            extract(""),
            {
                "update_id": "0",
                "chat_id": "0",
                "msg_text": "",
                "callback_id": "",
                "callback_data": "",
                "callback_msg_id": "0",
                "sender_name": "",
                "sender_username": "",
                "forward_user_id": "0",
            },
        )

    def test_beanshell_scripts_clean_and_cli_writes_valid_json(self) -> None:
        for script_fn in (
            gm.build_router_script,
            gm.build_init_status_script,
            gm.build_vision_script,
            gm.build_post_step_script,
            gm.build_timeout_script,
        ):
            src = script_fn()
            self.assertNotIn("{{", src)
            self.assertNotIn("}}", src)
            i, n, in_str = 0, len(src), False
            while i < n:
                ch = src[i]
                if ch == "\\" and in_str:
                    i += 2
                    continue
                if ch == '"':
                    in_str = not in_str
                elif ch == "\n" and in_str:
                    self.fail(f"Raw newline inside Java string in {script_fn.__name__}")
                i += 1
            py_src = compile_bsh_to_python(src, {})
            compile(py_src, script_fn.__name__, "exec")

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "Komobot_Controller.macro"
            with (
                mock.patch.object(gm, "OUT_MACRO", out_path),
                mock.patch(
                    "sys.argv",
                    [
                        "generate_macro.py",
                        "--bot-token",
                        "tok",
                        "--admin-id",
                        "111",
                        "--app-pin",
                        "0000",
                        "--app-name",
                        "pkg",
                    ],
                ),
            ):
                gm.main()
            written = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(written["macro"]["m_actionList"]), len(self.actions))


if __name__ == "__main__":
    unittest.main()
