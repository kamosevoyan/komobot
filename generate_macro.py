#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate Komobot_Controller.macro."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_MACRO = ROOT / "Komobot_Controller.macro"

# Pin pad coordinates calibrated for 720x1600 display (Telcell Wallet PIN screen)
PIN_COORDS: dict[str, tuple[int, int]] = {
    "1": (170, 1054),
    "2": (360, 1046),
    "3": (550, 1054),
    "4": (170, 1150),
    "5": (360, 1150),
    "6": (550, 1150),
    "7": (170, 1255),
    "8": (360, 1255),
    "9": (550, 1255),
    "0": (360, 1360),
}


class SiguidGen:
    """Deterministic negative 64-bit MacroDroid SIGUID generator."""

    def __init__(self, seed: str = "komobot-v2"):
        self.seed = seed
        self.counter = 0

    def next_id(self) -> int:
        self.counter += 1
        digest = hashlib.sha256(f"{self.seed}:{self.counter}".encode()).digest()
        val = int.from_bytes(digest[:8], "big", signed=False)
        return -((val % (2**62 - 1)) + 1000000000000000000)


def make_var(
    name: str, value: str = "", working: bool = False, supports_input: bool = True
) -> dict:
    """Build a MacroDroid local string variable definition."""
    return {
        "dictionary": {
            "entries": [],
            "isArray": False,
            "variableType": 4,
            "type": "Dictionary",
        },
        "isActionBlockWorkingVar": working,
        "isLocalVar": True,
        "isSecure": False,
        "m_booleanValue": False,
        "m_decimalValue": 0,
        "m_intValue": 0,
        "m_name": name,
        "m_stringValue": value,
        "m_type": 2,
        "supportsInput": supports_input,
        "supportsOutput": True,
    }


def make_extract_text(
    sg: SiguidGen, source_text: str, regex: str, target_var: str
) -> dict:
    """Build a TextManipulationAction (ExtractTextManipulation, group 1)."""
    return {
        "m_option": 2,
        "m_text": source_text,
        "m_textManipulation": {
            "type": "ExtractTextManipulation",
            "params": [regex, "1"],
        },
        "variableName": target_var,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "TextManipulationAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_java_action(
    sg: SiguidGen, script: str, response_var: str | None = None
) -> dict:
    """Build a JavaAction running in a blocking background thread."""
    action = {
        "blockNextAction": True,
        "runInBackgroundThread": True,
        "scriptText": script,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "JavaAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }
    if response_var:
        action["responseVariableName"] = response_var
    return action


def _make_if_var_string(
    sg: SiguidGen, var_name: str, expected: str, *, equals: bool = True
) -> dict:
    """Build an IfConditionAction checking string equality or inequality on a local var."""
    return {
        "childrenCollapsed": False,
        "dontLogIfConditionIsFalse": False,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "IfConditionAction",
        "m_comment": "",
        "m_constraintList": [
            {
                "checkCase": True,
                "dictionaryKeys": {"keys": []},
                "dictionaryType": 2,
                "enableRegex": False,
                "m_booleanValue": False,
                "m_doubleValue": 0,
                "m_intCompareVariable": False,
                "m_intGreaterThan": False,
                "m_intLessThan": False,
                "m_intNotEqual": False,
                "m_intValue": 0,
                "m_stringComparisonType": 0,
                "m_stringEqual": equals,
                "m_stringValue": expected,
                "m_variable": make_var(var_name),
                "disableLogging": False,
                "m_SIGUID": sg.next_id(),
                "m_classType": "MacroDroidVariableConstraint",
                "m_comment": "",
                "m_constraintList": [],
                "m_isDisabled": False,
                "m_isOrCondition": False,
            }
        ],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_if_var_equals(sg: SiguidGen, var_name: str, expected: str) -> dict:
    """Build an IfConditionAction checking string equality on a local variable."""
    return _make_if_var_string(sg, var_name, expected, equals=True)


def make_if_var_not_equals(sg: SiguidGen, var_name: str, unexpected: str) -> dict:
    """Build an IfConditionAction checking string inequality on a local variable."""
    return _make_if_var_string(sg, var_name, unexpected, equals=False)


def make_end_if(sg: SiguidGen) -> dict:
    return {
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "EndIfAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_loop(sg: SiguidGen, count: int) -> dict:
    return {
        "childrenCollapsed": False,
        "m_fixedOptionCount": count,
        "m_option": 0,
        "timedDurationValue": 1,
        "timedTimeUnit": 0,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "LoopAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_end_loop(sg: SiguidGen) -> dict:
    return {
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "EndLoopAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_break_loop(sg: SiguidGen) -> dict:
    return {
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "BreakFromLoopAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_screen_on(sg: SiguidGen, screen_off: bool) -> dict:
    return {
        "m_pieLockScreen": False,
        "m_screenOff": screen_off,
        "m_screenOffNoLock": False,
        "m_screenOnAlternative": False,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "ScreenOnAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_launch_app(sg: SiguidGen, app_name: str, package_name: str) -> dict:
    return {
        "m_applicationName": app_name,
        "m_excludeFromRecents": False,
        "m_packageToLaunch": package_name,
        "m_startNew": False,
        "m_userSerial": -1,
        "m_workProfile": False,
        "option": 0,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "LaunchActivityAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_pause(
    sg: SiguidGen, seconds: int = 0, millis: int = 0, use_alarm: bool = False
) -> dict:
    return {
        "m_delayInMilliSeconds": millis,
        "m_delayInSeconds": seconds,
        "m_useAlarm": use_alarm,
        "unitForVariables": 0,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "PauseAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def _make_ui_interaction(sg: SiguidGen, ui_config: dict) -> dict:
    """Wrap a MacroDroid Accessibility UIInteractionAction payload."""
    return {
        "action": 0,
        "uiInteractionConfiguration": ui_config,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "UIInteractionAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_click_xy(sg: SiguidGen, x: int, y: int) -> dict:
    """Perform an Accessibility tap at fixed screen pixel coordinates."""
    return _make_ui_interaction(
        sg,
        {
            "blocking": False,
            "checkOverlays": False,
            "clickOption": 2,
            "contentDescription": "",
            "contextClick": False,
            "longClick": False,
            "showTouchLocation": False,
            "skipCount": "0",
            "textContent": "",
            "textMatchOption": 0,
            "useRegex": False,
            "viewId": "",
            "xyPercentages": False,
            "xyPoint": {"x": x, "y": y},
            "type": "Click",
        },
    )


def make_gesture_swipe(
    sg: SiguidGen,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 200,
) -> dict:
    """Perform a single-finger Accessibility swipe gesture between pixel coordinates."""
    return _make_ui_interaction(
        sg,
        {
            "additionalFingers": 0,
            "durationMs": duration_ms,
            "endX": end_x,
            "endY": end_y,
            "endX2": 0,
            "endY2": 0,
            "showTouchLocation": False,
            "startX": start_x,
            "startY": start_y,
            "startX2": 0,
            "startY2": 0,
            "type": "Gesture",
            "waitBeforeNext": True,
            "xyPercentages": False,
        },
    )


SCREENSHOT_DIR = "/storage/emulated/0/komobot_ss"
SCREENSHOT_FILE_BASE = "frame"


def make_take_screenshot(sg: SiguidGen) -> dict:
    """Build TakeScreenshotAction using direct Android 11+ Accessibility capture."""
    return {
        "customAllFilesPath": SCREENSHOT_DIR,
        "customFilename": SCREENSHOT_FILE_BASE,
        "emailSubject": "Screenshot",
        "m_mechanismOption": 0,
        "m_option": 0,
        "saveToJpeg": False,
        "screenshotFormat": 1,
        "uiOption": 1,
        "useCustomFilename": True,
        "useCustomSaveLocation": True,
        "useSmtpEmail": False,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "TakeScreenshotAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


_BSH_PROGRESS_HELPER = """String formatProgress(String label, int pct) {
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    int filled = pct / 10;
    StringBuilder bar = new StringBuilder();
    for (int i = 0; i < 10; i++) {
        if (i < filled) {
            bar.append("🟩");
        } else {
            bar.append("⬜");
        }
    }
    return label + "\\n" + bar.toString() + " " + pct + "%";
}"""

_BSH_READ_STREAM = """String readStream(InputStream is) throws Exception {
    if (is == null) return "";
    BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) {
        sb.append(line);
    }
    br.close();
    return sb.toString();
}"""

_BSH_FRAME_HELPER = f"""void deletePrivateFrames() {{
    try {{
        File png = new File("{SCREENSHOT_DIR}/{SCREENSHOT_FILE_BASE}.png");
        if (png.exists()) png.delete();
        File jpg = new File("{SCREENSHOT_DIR}/{SCREENSHOT_FILE_BASE}.jpg");
        if (jpg.exists()) jpg.delete();
    }} catch (Exception e) {{
    }}
}}"""

_BSH_TG_HTTP_HELPERS = """JSONObject tgPost(String method, JSONObject payload, int timeoutMs) {
    HttpURLConnection conn = null;
    try {
        URL url = new URL("https://api.telegram.org/bot" + botToken + "/" + method);
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(timeoutMs);
        conn.setReadTimeout(timeoutMs);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        conn.setRequestProperty("Connection", "keep-alive");
        byte[] outBytes = payload.toString().getBytes("UTF-8");
        OutputStream os = conn.getOutputStream();
        os.write(outBytes);
        os.flush();
        os.close();
        int code = conn.getResponseCode();
        InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();
        String resp = readStream(is);
        if (resp.length() > 0) {
            return new JSONObject(resp);
        }
    } catch (Exception e) {
        if (conn != null) {
            try {
                conn.disconnect();
            } catch (Exception ignored) {
            }
        }
    }
    return new JSONObject();
}

void tgJson(String method, JSONObject payload) {
    tgPost(method, payload, 5000);
}

JSONObject sendMsg(long cid, String text, JSONObject markup) {
    try {
        JSONObject body = new JSONObject();
        body.put("chat_id", cid);
        body.put("text", text);
        if (markup != null) {
            body.put("reply_markup", markup);
        }
        return tgPost("sendMessage", body, 6000);
    } catch (Exception e) {
        return new JSONObject();
    }
}

void updateStatus(long cid, long mid, String text) {
    if (cid <= 0L || mid <= 0L || text == null || text.length() == 0) return;
    try {
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        payload.put("text", text);
        tgPost("editMessageText", payload, 5000);
    } catch (Exception e) {
    }
}

void deleteStatus(long cid, long mid) {
    if (cid <= 0L || mid <= 0L) return;
    try {
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        tgPost("deleteMessage", payload, 5000);
    } catch (Exception e) {
    }
}"""

_BSH_WORKER_CONFIG_HELPERS = """JSONObject loadConfig() {
    File f = new File(configPath);
    if (f.exists()) {
        try {
            FileInputStream fis = new FileInputStream(f);
            String raw = readStream(fis);
            fis.close();
            if (raw.length() > 0) return new JSONObject(raw);
        } catch (Exception e) {
        }
    }
    return new JSONObject();
}

void saveConfig(JSONObject cfg) {
    try {
        synchronized (System.class) {
            JSONObject fresh = loadConfig();
            if (fresh.optLong("run_start_ms", 0L) > cfg.optLong("run_start_ms", 0L) && cfg.optLong("run_start_ms", 0L) > 0L) {
                return;
            }
            if (!cfg.optBoolean("_pop_queue", false)) {
                if (fresh.has("queue")) {
                    cfg.put("queue", fresh.getJSONArray("queue"));
                }
                if (fresh.optLong("busy_until", 0L) > cfg.optLong("busy_until", 0L) && cfg.optLong("busy_until", 0L) > 0L) {
                    cfg.put("busy_until", fresh.optLong("busy_until", 0L));
                }
            }
            cfg.remove("_pop_queue");
            if (fresh.optLong("last_update_id", 0L) > cfg.optLong("last_update_id", 0L)) {
                cfg.put("last_update_id", fresh.optLong("last_update_id", 0L));
            }
            if (fresh.optLong("status_message_id", 0L) > 0L && cfg.optLong("status_message_id", 0L) == 0L &&
                fresh.optLong("active_chat_id", 0L) == cfg.optLong("active_chat_id", 0L) &&
                fresh.optLong("run_start_ms", 0L) == cfg.optLong("run_start_ms", 0L)) {
                cfg.put("status_message_id", fresh.optLong("status_message_id", 0L));
            }
            if (fresh.has("allowed_users")) {
                cfg.put("allowed_users", fresh.getJSONArray("allowed_users"));
            }
            if (fresh.has("public_access")) {
                cfg.put("public_access", fresh.optBoolean("public_access", true));
            }
            File outFile = new File(configPath);
            if (outFile.getParentFile() != null && !outFile.getParentFile().exists()) {
                outFile.getParentFile().mkdirs();
            }
            FileOutputStream fos = new FileOutputStream(outFile);
            OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
            osw.write(cfg.toString(2));
            osw.flush();
            osw.close();
        }
    } catch (Exception e) {
    }
}"""


def build_router_script() -> str:
    """BeanShell Java 7 script for Telegram routing, auth, and user management."""
    return f"""import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONArray;
import org.json.JSONObject;

String botToken = "{{lv=bot_token}}".trim();
String appName = "{{lv=app_name}}".trim();
long defaultAdminId = 0L;
try {{
    defaultAdminId = Long.parseLong("{{lv=admin_id}}".trim());
}} catch (Exception e) {{
}}
String configPath = "/storage/emulated/0/Download/komobot_config.json";
String chatIdStr = "{{lv=chat_id}}".trim();
String updateIdStr = "{{lv=update_id}}".trim();
String msgText = "{{lv=msg_text}}".trim();

{_BSH_READ_STREAM}

{_BSH_PROGRESS_HELPER}

{_BSH_FRAME_HELPER}

{_BSH_TG_HTTP_HELPERS}

JSONObject loadConfig() {{
    File f = new File(configPath);
    if (f.exists()) {{
        try {{
            FileInputStream fis = new FileInputStream(f);
            String raw = readStream(fis);
            fis.close();
            if (raw.length() > 0) {{
                return new JSONObject(raw);
            }}
        }} catch (Exception e) {{
        }}
    }}
    JSONObject cfg = new JSONObject();
    cfg.put("admin_id", defaultAdminId);
    JSONArray users = new JSONArray();
    users.put(defaultAdminId);
    users.put(879155028L);
    cfg.put("allowed_users", users);
    cfg.put("public_access", true);
    cfg.put("busy_until", 0L);
    cfg.put("last_update_id", 0L);
    return cfg;
}}

void saveConfig(JSONObject cfg) {{
    try {{
        File f = new File(configPath);
        if (f.getParentFile() != null && !f.getParentFile().exists()) {{
            f.getParentFile().mkdirs();
        }}
        FileOutputStream fos = new FileOutputStream(f);
        OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
        osw.write(cfg.toString(2));
        osw.flush();
        osw.close();
    }} catch (Exception e) {{
    }}
}}

long cid = 0L;
try {{
    cid = Long.parseLong(chatIdStr);
}} catch (Exception e) {{
    return "IGNORE";
}}
if (cid == 0L) {{
    return "IGNORE";
}}

long uid = 0L;
try {{
    uid = Long.parseLong(updateIdStr);
}} catch (Exception e) {{
}}

String actionResult = "IGNORE";
String replyText = null;
JSONObject replyMarkup = null;
String statusStage = "";
int qPos = 0;
boolean dupUid = false;
boolean isAdminUser = false;
JSONArray coopPreemptNotices = null;
long coopRunStart = 0L;

// Wait briefly if a new worker is starting Stage 3 or exiting Stage 5 to avoid MacroDroid shared-local-var races
boolean sawExitWait = false;
boolean exitClearedCleanly = false;
long waitDeadline = System.currentTimeMillis() + 2000L;
while (System.currentTimeMillis() < waitDeadline) {{
    JSONObject probe = loadConfig();
    long pendMs = probe.optLong("worker_pending_start_ms", 0L);
    long bUntil = probe.optLong("busy_until", 0L);
    long exitMs = probe.optLong("worker_exiting_ms", 0L);
    long nMs = System.currentTimeMillis();
    boolean pendActive = pendMs > 0L && bUntil > 0L && (nMs - pendMs) < 2000L;
    boolean exitActive = exitMs > 0L && bUntil == 0L && (nMs - exitMs) < 800L;
    if (exitActive) {{
        sawExitWait = true;
    }}
    if (!pendActive && !exitActive) {{
        if (sawExitWait && exitMs == 0L) {{
            exitClearedCleanly = true;
        }}
        break;
    }}
    try {{
        Thread.sleep(25L);
    }} catch (Exception e) {{
        break;
    }}
}}
if (exitClearedCleanly) {{
    try {{
        Thread.sleep(100L);
    }} catch (Exception e) {{
    }}
}}

synchronized (System.class) {{
    JSONObject cfg = loadConfig();
    long lastUid = cfg.optLong("last_update_id", 0L);
    if (uid > 0L && uid <= lastUid) {{
        dupUid = true;
    }} else {{
        if (uid > 0L) {{
            cfg.put("last_update_id", uid);
        }}
        cfg.put("last_chat_id", cid);
        cfg.put("last_msg_text", msgText);

        long adminId = cfg.optLong("admin_id", defaultAdminId);
        if (!cfg.has("admin_id") && adminId > 0L) {{
            cfg.put("admin_id", adminId);
        }}
        JSONArray allowed = cfg.optJSONArray("allowed_users");
        if (allowed == null) {{
            allowed = new JSONArray();
            allowed.put(adminId);
            cfg.put("allowed_users", allowed);
        }}

        boolean isAdmin = (cid == adminId);
        isAdminUser = isAdmin;
        boolean isAllowed = isAdmin;
        for (int i = 0; i < allowed.length(); i++) {{
            if (allowed.optLong(i, 0L) == cid) {{
                isAllowed = true;
                break;
            }}
        }}

        if (!isAllowed) {{
            saveConfig(cfg);
            replyText = "⛔ Unauthorized. Your ID: " + cid;
        }} else if (msgText.equals("/start")) {{
            JSONObject markup = new JSONObject();
            markup.put("resize_keyboard", true);
            JSONArray keyboard = new JSONArray();
            if (isAdmin) {{
                JSONArray r1 = new JSONArray();
                r1.put("📸 Take QR Screenshot");
                JSONArray r2 = new JSONArray();
                r2.put("👥 List Users");
                r2.put("🛑 Toggle Public Access");
                JSONArray r3 = new JSONArray();
                r3.put("🧹 Reset VM App");
                keyboard.put(r1);
                keyboard.put(r2);
                keyboard.put(r3);
                markup.put("keyboard", keyboard);
                saveConfig(cfg);
                replyText = "👑 Admin Dashboard\\nUse /adduser <id>, /removeuser <id>, /listusers, /toggle to manage access.";
                replyMarkup = markup;
            }} else {{
                JSONArray r1 = new JSONArray();
                r1.put("📸 Take QR Screenshot");
                keyboard.put(r1);
                markup.put("keyboard", keyboard);
                saveConfig(cfg);
                replyText = "Welcome! Press the button below to generate a QR code.";
                replyMarkup = markup;
            }}
        }} else if (isAdmin && msgText.startsWith("/adduser")) {{
            String arg = msgText.substring(8).trim();
            try {{
                long newId = Long.parseLong(arg);
                boolean exists = false;
                for (int i = 0; i < allowed.length(); i++) {{
                    if (allowed.optLong(i, 0L) == newId) {{
                        exists = true;
                        break;
                    }}
                }}
                if (!exists) {{
                    allowed.put(newId);
                }}
                cfg.put("allowed_users", allowed);
                saveConfig(cfg);
                replyText = "✅ User " + newId + " added.";
            }} catch (Exception e) {{
                saveConfig(cfg);
                replyText = "⚠️ Usage: /adduser <telegram_id>";
            }}
        }} else if (isAdmin && msgText.startsWith("/removeuser")) {{
            String arg = msgText.substring(11).trim();
            try {{
                long remId = Long.parseLong(arg);
                JSONArray next = new JSONArray();
                boolean found = false;
                for (int i = 0; i < allowed.length(); i++) {{
                    long cur = allowed.optLong(i, 0L);
                    if (cur == remId) {{
                        found = true;
                    }} else {{
                        next.put(cur);
                    }}
                }}
                cfg.put("allowed_users", next);
                saveConfig(cfg);
                if (found) {{
                    replyText = "🗑️ User " + remId + " removed.";
                }} else {{
                    replyText = "🛑 User " + remId + " is not in the allowed list.";
                }}
            }} catch (Exception e) {{
                saveConfig(cfg);
                replyText = "⚠️ Usage: /removeuser <telegram_id>";
            }}
        }} else if (isAdmin && (msgText.equals("/listusers") || msgText.indexOf("List Users") >= 0)) {{
            saveConfig(cfg);
            if (allowed.length() == 0) {{
                replyText = "👥 The allowed users list is currently empty.";
            }} else {{
                StringBuilder sb = new StringBuilder();
                sb.append("👥 Allowed Users (").append(allowed.length()).append("):\\n\\n");
                for (int i = 0; i < allowed.length(); i++) {{
                    sb.append("• ").append(allowed.optLong(i)).append("\\n");
                }}
                replyText = sb.toString();
            }}
        }} else if (isAdmin && (msgText.equals("/toggle") || msgText.indexOf("Toggle Public Access") >= 0)) {{
            boolean pub = !cfg.optBoolean("public_access", true);
            cfg.put("public_access", pub);
            saveConfig(cfg);
            replyText = "Public access is now " + (pub ? "🟢 ENABLED." : "🔴 DISABLED.");
        }} else if (msgText.startsWith("/") && !msgText.equalsIgnoreCase("/qr")) {{
            saveConfig(cfg);
            replyText = "ℹ️ Commands: /start, /qr" + (isAdmin ? ", /adduser <id>, /removeuser <id>, /listusers, /toggle" : "");
        }} else {{
            boolean pubAccess = cfg.optBoolean("public_access", true);
            if (!pubAccess && !isAdmin) {{
                saveConfig(cfg);
                replyText = "⚠️ The bot is currently locked by the admin.";
            }} else {{
                long now = System.currentTimeMillis();
                long busyUntil = cfg.optLong("busy_until", 0L);
                String lowerMsg = msgText.toLowerCase();
                String requestedMode = "";
                if (isAdmin && msgText.indexOf("Reset VM") >= 0) {{
                    requestedMode = "reset";
                }} else if (lowerMsg.equals("/qr") || lowerMsg.equals("qr") || msgText.indexOf("Take QR Screenshot") >= 0 || lowerMsg.indexOf("qr") >= 0 || lowerMsg.indexOf("screenshot") >= 0) {{
                    requestedMode = "qr";
                }}
                boolean isResetPreempt = (now < busyUntil)
                    && requestedMode.equals("reset")
                    && !cfg.optString("capture_mode", "qr").equals("reset");
                boolean workerActive = cfg.optBoolean("worker_active", false);
                long heartbeatMs = cfg.optLong("worker_heartbeat_ms", 0L);
                boolean isLiveWorker = workerActive && heartbeatMs > 0L && (now - heartbeatMs) < 20000L;

                if (now < busyUntil && !isResetPreempt) {{
                    if (cid == cfg.optLong("active_chat_id", 0L)) {{
                        saveConfig(cfg);
                        if (now - cfg.optLong("run_start_ms", 0L) >= 3000L) {{
                            replyText = "⏳ Your request is already in progress.";
                        }}
                    }} else {{
                        JSONArray queue = cfg.optJSONArray("queue");
                        if (queue == null) {{
                            queue = new JSONArray();
                        }}
                        int dupIdx = -1;
                        for (int i = 0; i < queue.length(); i++) {{
                            JSONObject qItem = queue.optJSONObject(i);
                            if (qItem != null && qItem.optLong("chat_id", 0L) == cid) {{
                                dupIdx = i;
                                break;
                            }}
                        }}
                        if (dupIdx >= 0) {{
                            saveConfig(cfg);
                            replyText = "⏳ You are already in the queue (#" + (dupIdx + 1) + ").";
                        }} else {{
                            qPos = queue.length() + 1;
                            JSONObject item = new JSONObject();
                            item.put("chat_id", cid);
                            item.put("status_message_id", 0L);
                            queue.put(item);
                            cfg.put("queue", queue);
                            cfg.put("busy_until", busyUntil + 30000L);
                            saveConfig(cfg);
                            statusStage = "QUEUE";
                        }}
                    }}
                }} else {{
                    if (requestedMode.length() == 0) {{
                        saveConfig(cfg);
                    }} else {{
                        JSONArray displaced = new JSONArray();
                        if (isResetPreempt) {{
                            long prevCid = cfg.optLong("active_chat_id", 0L);
                            long prevMid = cfg.optLong("status_message_id", 0L);
                            if (prevCid != 0L) {{
                                JSONObject pActive = new JSONObject();
                                pActive.put("chat_id", prevCid);
                                pActive.put("status_message_id", prevMid);
                                displaced.put(pActive);
                            }}
                            JSONArray prevQ = cfg.optJSONArray("queue");
                            if (prevQ != null) {{
                                for (int qi = 0; qi < prevQ.length(); qi++) {{
                                    JSONObject qItem = prevQ.optJSONObject(qi);
                                    if (qItem != null && qItem.optLong("chat_id", 0L) != 0L) {{
                                        displaced.put(qItem);
                                    }}
                                }}
                            }}
                        }}
                        long prevStart = cfg.optLong("run_start_ms", 0L);
                        long runStart = (now > prevStart) ? now : (prevStart + 1L);
                        long leaseMs = requestedMode.equals("reset") ? 60000L : 45000L;
                        cfg.put("busy_until", now + leaseMs);
                        cfg.put("active_chat_id", cid);
                        cfg.put("app_name", appName);
                        cfg.put("capture_mode", requestedMode);
                        cfg.put("queue", new JSONArray());
                        cfg.put("qr_was_closed", false);
                        cfg.put("reset_notified", false);
                        cfg.put("reset_stage", 0);
                        cfg.put("reset_kills", 0);
                        cfg.put("reset_recents_checked", false);
                        cfg.put("reset_open_tries", 0);
                        cfg.put("step_count", 0);
                        cfg.put("other_count", 0);
                        cfg.put("white_count", 0);
                        cfg.put("loading_count", 0);
                        cfg.put("last_state", "INIT");
                        cfg.put("progress_pct", isAdmin ? 0 : 10);
                        cfg.put("pending_status_text", "");
                        cfg.put("last_ss_deleted", true);
                        cfg.put("run_start_ms", runStart);
                        cfg.put("status_message_id", 0L);
                        cfg.put("worker_active", true);
                        cfg.put("worker_heartbeat_ms", now);
                        cfg.put("worker_exiting_ms", 0L);

                        if (isResetPreempt && isLiveWorker) {{
                            cfg.put("preempted_notices", new JSONArray());
                            saveConfig(cfg);
                            coopPreemptNotices = displaced;
                            coopRunStart = runStart;
                            statusStage = "COOP_RESET";
                            actionResult = "IGNORE";
                        }} else {{
                            JSONArray preemptNotices = cfg.optJSONArray("preempted_notices");
                            if (preemptNotices == null) {{
                                preemptNotices = new JSONArray();
                            }}
                            for (int di = 0; di < displaced.length(); di++) {{
                                preemptNotices.put(displaced.get(di));
                            }}
                            cfg.put("preempted_notices", preemptNotices);
                            cfg.put("vm_booting", false);
                            cfg.put("worker_pending_start_ms", now);
                            cfg.put("worker_start_ms", runStart);
                            saveConfig(cfg);
                            deletePrivateFrames();
                            actionResult = "RUN";
                        }}
                    }}
                }}
            }}
        }}
    }}
}}

if (dupUid) {{
    return "IGNORE";
}}
if (actionResult.equals("RUN")) {{
    return "RUN";
}}
if (statusStage.equals("COOP_RESET")) {{
    JSONObject sent = sendMsg(cid, "🔄 Force-restarting Telcell Wallet...", null);
    long resetMsgId = sent.has("result") ? sent.getJSONObject("result").optLong("message_id", 0L) : 0L;
    if (resetMsgId > 0L) {{
        synchronized (System.class) {{
            JSONObject fresh = loadConfig();
            if (fresh.optLong("active_chat_id", 0L) == cid
                && fresh.optLong("run_start_ms", 0L) == coopRunStart
                && fresh.optLong("status_message_id", 0L) == 0L) {{
                fresh.put("status_message_id", resetMsgId);
                fresh.put("last_ss_deleted", true);
                saveConfig(fresh);
            }}
        }}
    }}
    if (coopPreemptNotices != null) {{
        for (int ni = 0; ni < coopPreemptNotices.length(); ni++) {{
            JSONObject nItem = coopPreemptNotices.optJSONObject(ni);
            if (nItem != null) {{
                long nCid = nItem.optLong("chat_id", 0L);
                long nMid = nItem.optLong("status_message_id", 0L);
                if (nCid != 0L) {{
                    String cancelMsg = "❌ Request cancelled by VM reset. Please try again.";
                    if (nMid > 0L) {{
                        updateStatus(nCid, nMid, cancelMsg);
                    }} else {{
                        sendMsg(nCid, cancelMsg, null);
                    }}
                }}
            }}
        }}
    }}
    return "IGNORE";
}}
if (replyText != null) {{
    sendMsg(cid, replyText, replyMarkup);
}} else if (statusStage.equals("QUEUE")) {{
    String qText = isAdminUser
        ? "⏳ Queued (#" + qPos + ") — waiting for current request to finish..."
        : formatProgress("⏳ Queued (#" + qPos + ")...", 0);
    JSONObject qSent = sendMsg(cid, qText, null);
    long qMsgId = qSent.has("result") ? qSent.getJSONObject("result").optLong("message_id", 0L) : 0L;
    if (qMsgId > 0L) {{
        synchronized (System.class) {{
            JSONObject fresh = loadConfig();
            JSONArray q = fresh.optJSONArray("queue");
            boolean updated = false;
            if (q != null) {{
                for (int i = 0; i < q.length(); i++) {{
                    JSONObject qi = q.optJSONObject(i);
                    if (qi != null && qi.optLong("chat_id", 0L) == cid && qi.optLong("status_message_id", 0L) == 0L) {{
                        qi.put("status_message_id", qMsgId);
                        updated = true;
                        break;
                    }}
                }}
            }}
            if (updated) {{
                saveConfig(fresh);
            }}
        }}
    }}
}}
return actionResult;
"""


def build_init_status_script() -> str:
    """BeanShell Java 7 script sending initial status while Virtual Master boots."""
    return (
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import org.json.JSONArray;\n"
        "import org.json.JSONObject;\n\n"
        'String botToken = "{lv=bot_token}".trim();\n'
        'String configPath = "/storage/emulated/0/Download/komobot_config.json";\n\n'
        + _BSH_READ_STREAM
        + "\n\n"
        + _BSH_PROGRESS_HELPER
        + "\n\n"
        + _BSH_FRAME_HELPER
        + "\n\n"
        + _BSH_TG_HTTP_HELPERS
        + "\n\n"
        + _BSH_WORKER_CONFIG_HELPERS
        + """

long t0 = System.currentTimeMillis();
deletePrivateFrames();

long cid = 0L;
long adminId = 0L;
long claimedRunStart = 0L;
long existingMid = 0L;
String captureMode = "qr";
synchronized (System.class) {
    JSONObject cfg = loadConfig();
    cfg.put("worker_pending_start_ms", 0L);
    cfg.put("worker_heartbeat_ms", System.currentTimeMillis());
    saveConfig(cfg);
    cid = cfg.optLong("active_chat_id", 0L);
    adminId = cfg.optLong("admin_id", 0L);
    claimedRunStart = cfg.optLong("run_start_ms", 0L);
    existingMid = cfg.optLong("status_message_id", 0L);
    captureMode = cfg.optString("capture_mode", "qr");
}
if (cid <= 0L || existingMid > 0L) {
    return "SKIP";
}

String initText = captureMode.equals("reset")
    ? "🔄 Force-restarting Telcell Wallet..."
    : ((cid == adminId)
        ? "🔍 Waking phone & checking Virtual Master..."
        : formatProgress("⏳ Generating QR code...", 10));
JSONObject sent = sendMsg(cid, initText, null);
long statusMsgId = sent.has("result") ? sent.getJSONObject("result").optLong("message_id", 0L) : 0L;
JSONArray preemptNotices = null;
boolean deleteOrphanedMsg = false;
synchronized (System.class) {
    JSONObject fresh = loadConfig();
    fresh.put("worker_heartbeat_ms", System.currentTimeMillis());
    boolean dirty = true;
    boolean sameOwner = fresh.optLong("active_chat_id", 0L) == cid && fresh.optLong("run_start_ms", 0L) == claimedRunStart;
    if (statusMsgId > 0L && sameOwner) {
        fresh.put("status_message_id", statusMsgId);
        fresh.put("last_ss_deleted", true);
    } else if (statusMsgId > 0L && !sameOwner) {
        deleteOrphanedMsg = true;
    }
    JSONArray pendingNotices = fresh.optJSONArray("preempted_notices");
    if (pendingNotices != null && pendingNotices.length() > 0) {
        preemptNotices = pendingNotices;
        fresh.put("preempted_notices", new JSONArray());
    }
    if (dirty) {
        saveConfig(fresh);
    }
}
if (deleteOrphanedMsg) {
    deleteStatus(cid, statusMsgId);
}
if (preemptNotices != null) {
    for (int i = 0; i < preemptNotices.length(); i++) {
        JSONObject nItem = preemptNotices.optJSONObject(i);
        if (nItem != null) {
            long nCid = nItem.optLong("chat_id", 0L);
            long nMid = nItem.optLong("status_message_id", 0L);
            if (nCid != 0L) {
                String cancelMsg = "❌ Request cancelled by VM reset. Please try again.";
                if (nMid > 0L) {
                    updateStatus(nCid, nMid, cancelMsg);
                } else {
                    sendMsg(nCid, cancelMsg, null);
                }
            }
        }
    }
}

long rem = 400L - (System.currentTimeMillis() - t0);
if (rem > 0L) {
    try {
        Thread.sleep(rem);
    } catch (Exception e) {
    }
}
return (statusMsgId > 0L) ? "SENT" : "ERR";
"""
    )


def build_vision_script() -> str:
    """BeanShell Java 7 script for screenshot polling, state machine & QR crop."""
    return (
        "import android.graphics.Bitmap;\n"
        "import android.graphics.BitmapFactory;\n"
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import org.json.JSONArray;\n"
        "import org.json.JSONObject;\n\n"
        'String botToken = "{lv=bot_token}".trim();\n'
        'String appName = "{lv=app_name}".trim();\n'
        'String configPath = "/storage/emulated/0/Download/komobot_config.json";\n\n'
        + _BSH_READ_STREAM
        + "\n\n"
        + _BSH_PROGRESS_HELPER
        + "\n\n"
        + _BSH_TG_HTTP_HELPERS
        + "\n\n"
        + _BSH_WORKER_CONFIG_HELPERS
        + f"""

JSONObject syncActiveConfig(JSONObject curCfg, String ssName, long ssMtime, boolean ssDel, boolean countStep) {{
    synchronized (System.class) {{
        JSONObject fresh = loadConfig();
        long curWStart = curCfg.optLong("worker_start_ms", 0L);
        long freshWStart = fresh.optLong("worker_start_ms", 0L);
        if (curWStart > 0L && freshWStart > curWStart) {{
            return null;
        }}
        long nowMs = System.currentTimeMillis();
        if (fresh.optLong("run_start_ms", 0L) > curCfg.optLong("run_start_ms", 0L)) {{
            fresh.put("vm_booting", curCfg.optBoolean("vm_booting", false));
            if (ssName != null) {{
                fresh.put("last_ss_name", ssName);
                fresh.put("last_ss_mtime", ssMtime);
                fresh.put("last_ss_deleted", ssDel);
            }}
            if (countStep) {{
                fresh.put("step_count", fresh.optInt("step_count", 0) + 1);
            }}
            fresh.put("worker_heartbeat_ms", nowMs);
            long mLease = nowMs + 30000L;
            if (fresh.optLong("busy_until", 0L) < mLease) {{
                fresh.put("busy_until", mLease);
            }}
            saveConfig(fresh);
            return fresh;
        }}
        if (fresh.optLong("status_message_id", 0L) > 0L
            && curCfg.optLong("status_message_id", 0L) == 0L
            && fresh.optLong("active_chat_id", 0L) == curCfg.optLong("active_chat_id", 0L)
            && fresh.optLong("run_start_ms", 0L) == curCfg.optLong("run_start_ms", 0L)) {{
            curCfg.put("status_message_id", fresh.optLong("status_message_id", 0L));
        }}
        curCfg.put("worker_heartbeat_ms", nowMs);
        saveConfig(curCfg);
        return curCfg;
    }}
}}

int sendPhotoBytes(long cid, byte[] pngBytes, String filename, String caption) {{
    HttpURLConnection conn = null;
    try {{
        URL url = new URL("https://api.telegram.org/bot" + botToken + "/sendPhoto");
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setDoOutput(true);
        String boundary = "*****" + System.currentTimeMillis() + "*****";
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        conn.setRequestProperty("Connection", "keep-alive");
        DataOutputStream req = new DataOutputStream(conn.getOutputStream());

        req.writeBytes("--" + boundary + "\\r\\n");
        req.writeBytes("Content-Disposition: form-data; name=\\"chat_id\\"\\r\\n\\r\\n");
        req.writeBytes(cid + "\\r\\n");

        if (caption != null && caption.length() > 0) {{
            req.writeBytes("--" + boundary + "\\r\\n");
            req.writeBytes("Content-Disposition: form-data; name=\\"caption\\"\\r\\n\\r\\n");
            req.write(caption.getBytes("UTF-8"));
            req.writeBytes("\\r\\n");
        }}

        req.writeBytes("--" + boundary + "\\r\\n");
        req.writeBytes("Content-Disposition: form-data; name=\\"photo\\"; filename=\\"" + filename + "\\"\\r\\n");
        req.writeBytes("Content-Type: image/png\\r\\n\\r\\n");
        req.write(pngBytes);
        req.writeBytes("\\r\\n--" + boundary + "--\\r\\n");
        req.flush();
        req.close();

        int code = conn.getResponseCode();
        InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();
        readStream(is);
        return code;
    }} catch (Exception e) {{
        if (conn != null) {{
            try {{
                conn.disconnect();
            }} catch (Exception ignored) {{
            }}
        }}
        return -1;
    }}
}}

boolean hasValidImageTrailer(File f) {{
    RandomAccessFile raf = null;
    boolean ok = false;
    try {{
        if (f == null || !f.exists()) return false;
        long flen = f.length();
        if (flen < 100L) return false;
        String lower = f.getName().toLowerCase();
        boolean isPng = lower.endsWith(".png");
        boolean isJpg = lower.endsWith(".jpg") || lower.endsWith(".jpeg");
        if (!isPng && !isJpg) return true;
        raf = new RandomAccessFile(f, "r");
        long maxTail = isPng ? 32L : 8L;
        int n = (flen < maxTail) ? (int) flen : (int) maxTail;
        raf.seek(flen - n);
        int m = 0;
        for (int i = 0; i < n; i++) {{
            int b = raf.read();
            if (b < 0) break;
            if (isPng) {{
                if (m == 0 && b == 73) m = 1;
                else if (m == 1 && b == 69) m = 2;
                else if (m == 2 && b == 78) m = 3;
                else if (m == 3 && b == 68) m = 4;
                else if (m == 4 && b == 174) m = 5;
                else if (m == 5 && b == 66) m = 6;
                else if (m == 6 && b == 96) m = 7;
                else if (m == 7 && b == 130) {{ ok = true; break; }}
                else m = (b == 73) ? 1 : 0;
            }} else {{
                if (m == 1 && b == 217) {{ ok = true; break; }}
                m = (b == 255) ? 1 : 0;
            }}
        }}
    }} catch (Exception e) {{
        ok = false;
    }} finally {{
        if (raf != null) {{
            try {{
                raf.close();
            }} catch (Exception ignored) {{
            }}
        }}
    }}
    return ok;
}}

boolean cleanScreenshots(String[] dirs, File latestFile, String latestName) {{
    boolean deleted = false;
    if (latestFile != null) {{
        try {{
            deleted = latestFile.delete();
        }} catch (Exception e) {{
        }}
    }}
    for (int i = 0; i < dirs.length; i++) {{
        File d = new File(dirs[i]);
        if (!d.exists() || !d.isDirectory()) continue;
        File[] files = d.listFiles();
        if (files == null) continue;
        for (int j = 0; j < files.length; j++) {{
            File f = files[j];
            String n = f.getName();
            if ((latestName != null && n.equals("thumbnail_" + latestName)) ||
                ((n.startsWith(".trashed-") || n.startsWith("thumbnail_")) &&
                 (n.indexOf("Virtual Master") >= 0 || n.indexOf("Virtual_Master") >= 0))) {{
                try {{
                    f.delete();
                }} catch (Exception e) {{
                }}
            }}
        }}
    }}
    return deleted;
}}

JSONObject cfg = null;
synchronized (System.class) {{
    cfg = loadConfig();
    cfg.put("worker_heartbeat_ms", System.currentTimeMillis());
    saveConfig(cfg);
}}
String mode = cfg.optString("capture_mode", "qr");
long cid = cfg.optLong("active_chat_id", 0L);
long adminId = cfg.optLong("admin_id", 0L);
long statusMsgId = cfg.optLong("status_message_id", 0L);
int prevStepCount = cfg.optInt("step_count", 0);
if (prevStepCount >= 95) {{
    return "ABORT_TIMEOUT";
}}
int stepCount = prevStepCount + 1;
cfg.put("step_count", stepCount);
long minLease = System.currentTimeMillis() + 30000L;
if (cfg.optLong("busy_until", 0L) < minLease) {{
    cfg.put("busy_until", minLease);
}}
long runStartMs = cfg.optLong("run_start_ms", System.currentTimeMillis() - 5000L);
String lastSsName = cfg.optString("last_ss_name", "");
long lastSsMtime = cfg.optLong("last_ss_mtime", 0L);
boolean lastSsDeleted = cfg.optBoolean("last_ss_deleted", false);

String[] dirs = new String[]{{
    "{SCREENSHOT_DIR}",
    "/storage/emulated/0/DCIM/Screenshots",
    "/storage/emulated/0/Pictures/Screenshots"
}};

long waitStart = System.currentTimeMillis();
long firstCandMs = 0L;
File latest = null;
boolean latestReady = false;
while (System.currentTimeMillis() - waitStart < 3800L) {{
    File cand = null;
    for (int i = 0; i < dirs.length; i++) {{
        File d = new File(dirs[i]);
        if (!d.exists() || !d.isDirectory()) continue;
        File[] files = d.listFiles();
        if (files == null) continue;
        for (int j = 0; j < files.length; j++) {{
            File f = files[j];
            String n = f.getName();
            boolean isPrivateFrame = (i == 0) && (n.equals("{SCREENSHOT_FILE_BASE}.png") || n.equals("{SCREENSHOT_FILE_BASE}.jpg"));
            boolean isSysShot = n.startsWith("Screenshot");
            if (f.isFile() && (isPrivateFrame || isSysShot) && f.length() > 5000L) {{
                long lm = f.lastModified();
                boolean acceptNew = lastSsDeleted || !n.equals(lastSsName) || lm > lastSsMtime;
                if (lm >= runStartMs - 2500L && acceptNew) {{
                    if (cand == null || lm > cand.lastModified()) {{
                        cand = f;
                    }}
                }}
            }}
        }}
    }}
    if (cand != null) {{
        latest = cand;
        if (firstCandMs == 0L) {{
            firstCandMs = System.currentTimeMillis();
        }}
        if (hasValidImageTrailer(latest)) {{
            latestReady = true;
            break;
        }}
        if (System.currentTimeMillis() - firstCandMs >= 1800L) {{
            break;
        }}
        Thread.sleep(20L);
    }} else {{
        Thread.sleep(40L);
    }}
}}

if (latest == null) {{
    JSONObject synced = syncActiveConfig(cfg, null, 0L, false, false);
    if (synced == null) {{
        return "ABORT_PREEMPTED";
    }}
    cfg = synced;
    cfg.put("last_state", "NO_SCREENSHOT");
    cfg.put("pending_status_text", "");
    saveConfig(cfg);
    return "WAIT";
}}

if (!latestReady) {{
    latestReady = hasValidImageTrailer(latest);
}}

String latestName = latest.getName();
long latestMtime = latest.lastModified();
cfg.put("last_ss_name", latestName);
cfg.put("last_ss_mtime", latestMtime);

if (!latestReady) {{
    boolean deletedNow = cleanScreenshots(dirs, latest, latestName);
    cfg.put("last_ss_deleted", deletedNow);
    JSONObject synced = syncActiveConfig(cfg, latestName, latestMtime, deletedNow, false);
    if (synced == null) {{
        return "ABORT_PREEMPTED";
    }}
    cfg = synced;
    cfg.put("last_state", "TRUNCATED_SS");
    cfg.put("pending_status_text", "");
    saveConfig(cfg);
    return "WAIT";
}}

Bitmap bmp = null;
for (int attempt = 0; attempt < 6; attempt++) {{
    bmp = BitmapFactory.decodeFile(latest.getAbsolutePath());
    if (bmp != null) break;
    Thread.sleep(35L);
}}

boolean deletedNow = cleanScreenshots(dirs, latest, latestName);
cfg.put("last_ss_deleted", deletedNow);

if (bmp == null) {{
    JSONObject synced = syncActiveConfig(cfg, latestName, latestMtime, deletedNow, false);
    if (synced == null) {{
        return "ABORT_PREEMPTED";
    }}
    cfg = synced;
    cfg.put("last_state", "DECODE_ERR");
    cfg.put("pending_status_text", "");
    saveConfig(cfg);
    return "WAIT";
}}

try {{
    JSONObject synced = syncActiveConfig(cfg, latestName, latestMtime, deletedNow, true);
    if (synced == null) {{
        return "ABORT_PREEMPTED";
    }}
    if (synced != cfg) {{
        cfg = synced;
        mode = cfg.optString("capture_mode", "qr");
        cid = cfg.optLong("active_chat_id", 0L);
        adminId = cfg.optLong("admin_id", 0L);
        stepCount = cfg.optInt("step_count", 1);
    }}
    statusMsgId = cfg.optLong("status_message_id", 0L);
    int w = bmp.getWidth();
    int h = bmp.getHeight();
    int px(int x) {{
        int v = (x * w) / 720;
        if (v < 0) return 0;
        if (v >= w) return w - 1;
        return v;
    }}
    int py(int y) {{
        int v = (y * h) / 1600;
        if (v < 0) return 0;
        if (v >= h) return h - 1;
        return v;
    }}
    int getR(int x, int y) {{ return (bmp.getPixel(px(x), py(y)) >> 16) & 0xFF; }}
    int getG(int x, int y) {{ return (bmp.getPixel(px(x), py(y)) >> 8) & 0xFF; }}
    int getB(int x, int y) {{ return bmp.getPixel(px(x), py(y)) & 0xFF; }}

    boolean isDark(int x, int y) {{
        return getR(x, y) < 45 && getG(x, y) < 45 && getB(x, y) < 45;
    }}
    boolean isWhite(int x, int y) {{
        return getR(x, y) > 235 && getG(x, y) > 235 && getB(x, y) > 235;
    }}
    boolean isOrange(int x, int y) {{
        int r = getR(x, y); int g = getG(x, y); int b = getB(x, y);
        return r > 205 && g >= 75 && g <= 155 && b >= 35 && b <= 125;
    }}
    boolean isPinGray(int x, int y) {{
        int r = getR(x, y); int g = getG(x, y); int b = getB(x, y);
        return r >= 225 && r <= 249 && g >= 225 && g <= 249 && b >= 228 && b <= 252 && Math.abs(r - g) <= 6;
    }}
    boolean isPopupCorner(int x, int y) {{
        int r = getR(x, y); int g = getG(x, y); int b = getB(x, y);
        return r >= 15 && r <= 42 && g >= 10 && g <= 35 && b >= 20 && b <= 48;
    }}
    boolean isRecentsBg(int x, int y) {{
        int r = getR(x, y); int g = getG(x, y); int b = getB(x, y);
        return r >= 200 && r <= 230 && g >= 200 && g <= 230 && b >= 212 && b <= 242 && (b - r) >= 6 && Math.abs(r - g) <= 6;
    }}
    boolean isRecentsCardPixel(int x, int y) {{
        int dr = Math.abs(getR(x, y) - getR(40, 800));
        int dg = Math.abs(getG(x, y) - getG(40, 800));
        int db = Math.abs(getB(x, y) - getB(40, 800));
        return (dr + dg + db) > 20 || !isRecentsBg(x, y);
    }}
    void resetWaitCounters(JSONObject cfg) throws Exception {{
        cfg.put("white_count", 0);
        cfg.put("loading_count", 0);
    }}
    String prepareStepStatus(JSONObject cfg, long targetCid, long adminId, String adminText, int userPct) {{
        if (targetCid == adminId) {{
            return adminText;
        }}
        int cur = cfg.optInt("progress_pct", 0);
        if (userPct <= cur) {{
            return null;
        }}
        if (userPct > 100) userPct = 100;
        cfg.put("progress_pct", userPct);
        return formatProgress("⏳ Generating QR code...", userPct);
    }}
    void queueStepStatus(JSONObject cfg, String text) throws Exception {{
        if (text != null && text.length() > 0) {{
            cfg.put("pending_status_text", text);
        }} else {{
            cfg.put("pending_status_text", "");
        }}
    }}
    String prepareWaitNudge(JSONObject cfg, long targetCid, long adminId, int waitStep, int capPct) {{
        if (targetCid == adminId) return null;
        if (waitStep != 2 && waitStep != 5) return null;
        int nextPct = cfg.optInt("progress_pct", 0) + 10;
        if (nextPct > capPct) nextPct = capPct;
        return prepareStepStatus(cfg, targetCid, adminId, null, nextPct);
    }}
    String handleLoadingWait(JSONObject cfg, String countKey, String stateName, int maxWaits, int waitCapPct, long cid, long adminId) throws Exception {{
        int cnt = cfg.optInt(countKey, 0) + 1;
        cfg.put(countKey, cnt);
        cfg.put("last_state", stateName);
        if (cnt <= maxWaits) {{
            String waitText = prepareWaitNudge(cfg, cid, adminId, cnt, waitCapPct);
            queueStepStatus(cfg, waitText);
            saveConfig(cfg);
            return "WAIT";
        }}
        queueStepStatus(cfg, null);
        if (cnt == maxWaits + 1) {{
            saveConfig(cfg);
            return "CLICK_BACK";
        }}
        if (cnt == maxWaits + 2) {{
            saveConfig(cfg);
            return "WAIT";
        }}
        cfg.put(countKey, 0);
        saveConfig(cfg);
        return "RESET_TO_HOME";
    }}
    String handleResetInApp(JSONObject cfg, long cid, long adminId) throws Exception {{
        cfg.put("vm_booting", false);
        int openTries = cfg.optInt("reset_open_tries", 0) + 1;
        cfg.put("reset_open_tries", openTries);
        cfg.put("reset_recents_checked", true);
        cfg.put("last_state", "RESET_OPEN_RECENTS");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        if (openTries == 1 || openTries == 3) {{
            String stepText = prepareStepStatus(cfg, cid, adminId, "🧹 Opening VM Recents...", 20);
            queueStepStatus(cfg, stepText);
            saveConfig(cfg);
            return "OPEN_RECENTS";
        }}
        queueStepStatus(cfg, null);
        if (openTries == 2 || openTries == 4) {{
            saveConfig(cfg);
            return "WAIT";
        }}
        if (openTries == 5) {{
            saveConfig(cfg);
            return "CLOSE_MODAL";
        }}
        if (openTries == 6) {{
            saveConfig(cfg);
            return "CLICK_BACK";
        }}
        cfg.put("reset_open_tries", 0);
        cfg.put("reset_stage", 1);
        saveConfig(cfg);
        return "RESET_TO_HOME";
    }}

    // 1. Check VM Launcher vs VM Boot Loading
    if (isDark(360, 800) && isDark(100, 500) && isDark(360, 350)) {{
        int enterMax = 0;
        for (int x = 595; x <= 670; x += 5) {{
            for (int y = 235; y <= 265; y += 5) {{
                int c = bmp.getPixel(px(x), py(y));
                int r = (c >> 16) & 0xFF;
                int g = (c >> 8) & 0xFF;
                int b = c & 0xFF;
                if (r > enterMax) enterMax = r;
                if (g > enterMax) enterMax = g;
                if (b > enterMax) enterMax = b;
            }}
        }}
        cfg.put("vm_booting", true);
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        if (enterMax > 120) {{
            cfg.put("last_state", "VM_LAUNCHER");
            String stepText = prepareStepStatus(cfg, cid, adminId, "🖥️ Entering Virtual Master...", 20);
            queueStepStatus(cfg, stepText);
            saveConfig(cfg);
            return "CLICK_ENTER";
        }}
        cfg.put("last_state", "VM_LOADING");
        String waitText = ((stepCount & 1) == 0) ? prepareWaitNudge(cfg, cid, adminId, 2, 20) : null;
        queueStepStatus(cfg, waitText);
        saveConfig(cfg);
        return "WAIT";
    }}

    // 2. Check Virtual Master 3x3 Floating Quick Menu Popup
    if (isPopupCorner(130, 590) && isPopupCorner(590, 590) &&
        isPopupCorner(130, 1050) && isPopupCorner(590, 1050) &&
        !(isDark(360, 350) && getB(360, 350) < 35)) {{
        cfg.put("last_state", "VM_POPUP");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        queueStepStatus(cfg, null);
        saveConfig(cfg);
        return "DISMISS_POPUP";
    }}

    int resetStage = cfg.optInt("reset_stage", 0);
    int resetKills = cfg.optInt("reset_kills", 0);
    boolean resetRecentsChecked = cfg.optBoolean("reset_recents_checked", false);
    boolean vmBooting = cfg.optBoolean("vm_booting", false);

    // 3. Check Virtual Master Recents Screen (#dad9e4 backdrop around card slot)
    if (isRecentsBg(40, 800) && isRecentsBg(620, 800) &&
        isRecentsBg(360, 200) && isRecentsBg(360, 1360)) {{
        cfg.put("vm_booting", false);
        cfg.put("other_count", 0);
        cfg.put("reset_open_tries", 0);
        cfg.put("reset_recents_checked", true);
        resetWaitCounters(cfg);
        if (mode.equals("reset") && resetStage == 0) {{
            boolean hasCard = isRecentsCardPixel(360, 500) || isRecentsCardPixel(360, 800) || isRecentsCardPixel(360, 1000);
            if (hasCard && resetKills < 3) {{
                cfg.put("reset_kills", resetKills + 1);
                cfg.put("last_state", "VM_RECENTS");
                String stepText = prepareStepStatus(cfg, cid, adminId, "🔪 Closing Telcell Wallet...", 25);
                queueStepStatus(cfg, stepText);
                saveConfig(cfg);
                return "SWIPE_KILL_RECENT";
            }}
            cfg.put("reset_stage", 1);
            cfg.put("last_state", "VM_RECENTS_EMPTY");
            queueStepStatus(cfg, null);
            saveConfig(cfg);
            return "RESET_TO_HOME";
        }}
        cfg.put("last_state", "VM_RECENTS");
        queueStepStatus(cfg, null);
        saveConfig(cfg);
        return "RESET_TO_HOME";
    }}

    // 4. Check VM Home Screen (Telcell icon orange pixels)
    if (isDark(360, 800)) {{
        int o1 = 0;
        for (int x = 80; x <= 120; x += 3) {{
            for (int y = 360; y <= 400; y += 3) {{
                if (getR(x, y) > 200 && getG(x, y) < 120 && getB(x, y) < 80) o1++;
            }}
        }}
        int o2 = 0;
        for (int x = 80; x <= 120; x += 3) {{
            for (int y = 120; y <= 165; y += 3) {{
                if (getR(x, y) > 200 && getG(x, y) < 120 && getB(x, y) < 80) o2++;
            }}
        }}
        if (o1 >= 15 || o2 >= 15) {{
            cfg.put("vm_booting", false);
            cfg.put("other_count", 0);
            cfg.put("reset_open_tries", 0);
            resetWaitCounters(cfg);
            if (mode.equals("reset") && resetStage == 0 && !resetRecentsChecked && resetKills == 0) {{
                cfg.put("reset_recents_checked", true);
                cfg.put("last_state", "RESET_CHECK_RECENTS");
                String stepText = prepareStepStatus(cfg, cid, adminId, "🧹 Checking running VM apps...", 20);
                queueStepStatus(cfg, stepText);
                saveConfig(cfg);
                return "OPEN_RECENTS";
            }}
            if (mode.equals("reset")) {{
                cfg.put("reset_stage", 2);
            }}
            cfg.put("last_state", (o1 >= 15) ? "VM_HOME_1" : "VM_HOME_2");
            String launchLabel = mode.equals("reset") ? "🚀 Reopening Telcell Wallet..." : "🚀 Launching Telcell Wallet...";
            String stepText = prepareStepStatus(cfg, cid, adminId, launchLabel, mode.equals("reset") ? 35 : 30);
            queueStepStatus(cfg, stepText);
            saveConfig(cfg);
            return (o1 >= 15) ? "LAUNCH_1" : "LAUNCH_2";
        }}
    }}

    // 5. Reset Phase 0 in-app intercept (skip during VM cold boot splash so VM reaches Home)
    if (mode.equals("reset") && resetStage == 0 && !vmBooting) {{
        return handleResetInApp(cfg, cid, adminId);
    }}

    // 6. Check QR Code Modal
    if (getR(30, 400) < 110 && getG(30, 400) < 110 && getB(30, 400) < 110 &&
        isWhite(150, 400) && isWhite(570, 400) && isWhite(130, 590) && isWhite(590, 590)) {{
        cfg.put("vm_booting", false);
        if (mode.equals("reset")) {{
            cfg.put("qr_was_closed", true);
            cfg.put("last_state", "RESET_CLOSE_QR");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            queueStepStatus(cfg, null);
            saveConfig(cfg);
            return "CLOSE_MODAL";
        }}
        int blacks = 0;
        int whites = 0;
        for (int x = 200; x <= 520; x += 6) {{
            int sx = (x * w) / 720;
            if (sx >= w) sx = w - 1;
            for (int y = 510; y <= 830; y += 6) {{
                int sy = (y * h) / 1600;
                if (sy >= h) sy = h - 1;
                int c = bmp.getPixel(sx, sy);
                int r = (c >> 16) & 0xFF;
                int g = (c >> 8) & 0xFF;
                int b = c & 0xFF;
                if (r < 50 && g < 50 && b < 50) blacks++;
                else if (r > 220 && g > 220 && b > 220) whites++;
            }}
        }}
        if (blacks >= 100 && whites >= 100) {{
            if (stepCount == 1 && !cfg.optBoolean("qr_was_closed", false)) {{
                cfg.put("qr_was_closed", true);
                cfg.put("last_state", "STALE_QR");
                cfg.put("other_count", 0);
                resetWaitCounters(cfg);
                String stepText = prepareStepStatus(cfg, cid, adminId, "🔄 Refreshing stale QR screen...", 50);
                queueStepStatus(cfg, stepText);
                saveConfig(cfg);
                return "CLOSE_MODAL";
            }}
            JSONObject preSendSync = syncActiveConfig(cfg, latestName, latestMtime, deletedNow, false);
            if (preSendSync == null) {{
                return "ABORT_PREEMPTED";
            }}
            if (preSendSync != cfg || !preSendSync.optString("capture_mode", "qr").equals("qr")) {{
                cfg = preSendSync;
                cfg.put("qr_was_closed", true);
                cfg.put("last_state", "RESET_CLOSE_QR");
                cfg.put("other_count", 0);
                resetWaitCounters(cfg);
                queueStepStatus(cfg, null);
                saveConfig(cfg);
                return "CLOSE_MODAL";
            }}
            statusMsgId = cfg.optLong("status_message_id", 0L);
            queueStepStatus(cfg, null);
            int cx = px(130);
            int cy = py(445);
            int cw = px(590) - cx;
            int ch = py(905) - cy;
            Bitmap qrBmp = Bitmap.createBitmap(bmp, cx, cy, cw, ch);
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            qrBmp.compress(Bitmap.CompressFormat.PNG, 100, baos);
            qrBmp.recycle();
            int code = sendPhotoBytes(cid, baos.toByteArray(), "qr.png", "🎫 QR Code");
            if (code == 200) {{
                deleteStatus(cid, statusMsgId);
            }} else {{
                String errText = (cid == adminId)
                    ? "❌ Failed to upload QR (HTTP " + code + ")."
                    : "❌ Failed to upload QR. Please try again.";
                updateStatus(cid, statusMsgId, errText);
                if (cid != adminId && cid > 0L && adminId > 0L) {{
                    sendMsg(adminId,
                        "⚠️ User request failed (chat_id: " + cid + ")\\nReason: QR upload failed (HTTP " + code + ")",
                        null);
                }}
            }}
            long popNextCid = 0L;
            long popNextMid = 0L;
            String nextText = null;
            boolean hasNext = false;
            boolean preemptedDuringSend = false;
            boolean workerSuperseded = false;
            synchronized (System.class) {{
                JSONObject latestCfg = loadConfig();
                long curWStart = cfg.optLong("worker_start_ms", 0L);
                long freshWStart = latestCfg.optLong("worker_start_ms", 0L);
                long nowMs = System.currentTimeMillis();
                if (curWStart > 0L && freshWStart > curWStart) {{
                    workerSuperseded = true;
                }} else if (latestCfg.optString("capture_mode", "qr").equals("reset")
                    || latestCfg.optLong("run_start_ms", 0L) > cfg.optLong("run_start_ms", 0L)) {{
                    latestCfg.put("last_ss_name", latestName);
                    latestCfg.put("last_ss_mtime", latestMtime);
                    latestCfg.put("last_ss_deleted", deletedNow);
                    latestCfg.put("qr_was_closed", true);
                    latestCfg.put("worker_heartbeat_ms", nowMs);
                    saveConfig(latestCfg);
                    preemptedDuringSend = true;
                }} else {{
                    JSONArray queue = latestCfg.optJSONArray("queue");
                    if (queue != null && queue.length() > 0) {{
                        JSONObject nextItem = queue.getJSONObject(0);
                        JSONArray rem = new JSONArray();
                        for (int qi = 1; qi < queue.length(); qi++) {{
                            rem.put(queue.get(qi));
                        }}
                        popNextCid = nextItem.optLong("chat_id", 0L);
                        popNextMid = nextItem.optLong("status_message_id", 0L);
                        long prevStart = cfg.optLong("run_start_ms", 0L);
                        long nextRunStart = (nowMs > prevStart) ? nowMs : (prevStart + 1L);
                        cfg.put("_pop_queue", true);
                        cfg.put("queue", rem);
                        cfg.put("active_chat_id", popNextCid);
                        cfg.put("status_message_id", popNextMid);
                        cfg.put("run_start_ms", nextRunStart);
                        cfg.put("qr_was_closed", true);
                        cfg.put("step_count", 2);
                        cfg.put("other_count", 0);
                        resetWaitCounters(cfg);
                        cfg.put("busy_until", nowMs + 45000L);
                        cfg.put("worker_heartbeat_ms", nowMs);
                        cfg.put("last_state", "NEXT_IN_QUEUE");
                        cfg.put("progress_pct", (popNextCid == adminId) ? 0 : 70);
                        nextText = (popNextCid == adminId)
                            ? "🔄 Generating QR code for your request..."
                            : formatProgress("⏳ Generating QR code...", 70);
                        queueStepStatus(cfg, nextText);
                        saveConfig(cfg);
                        hasNext = true;
                    }} else {{
                        cfg.put("_pop_queue", true);
                        cfg.put("queue", new JSONArray());
                        cfg.put("last_state", "QR_SENT");
                        cfg.put("busy_until", 0L);
                        cfg.put("worker_active", false);
                        cfg.put("worker_pending_start_ms", 0L);
                        cfg.put("worker_exiting_ms", nowMs);
                        cfg.put("worker_heartbeat_ms", nowMs);
                        cfg.put("progress_pct", 0);
                        resetWaitCounters(cfg);
                        saveConfig(cfg);
                    }}
                }}
            }}
            if (workerSuperseded) {{
                return "ABORT_PREEMPTED";
            }}
            if (preemptedDuringSend || hasNext) {{
                return "CLOSE_MODAL";
            }}
            return "DONE";
        }}
        cfg.put("white_count", 0);
        return handleLoadingWait(cfg, "loading_count", "QR_LOADING", 9, 80, cid, adminId);
    }}

    // 7. Check Telcell PIN Screen (gray background + top orange Telcell logo)
    if (isPinGray(100, 500) && isPinGray(360, 1372)) {{
        int pinLogo = 0;
        for (int x = 280; x <= 440; x += 6) {{
            for (int y = 120; y <= 220; y += 6) {{
                if (getR(x, y) > 200 && getG(x, y) < 130 && getB(x, y) < 100) pinLogo++;
            }}
        }}
        if (pinLogo >= 10) {{
            cfg.put("vm_booting", false);
            if (mode.equals("reset") && resetStage == 0) {{
                return handleResetInApp(cfg, cid, adminId);
            }}
            int spinner = 0;
            for (int x = 330; x <= 390; x += 3) {{
                for (int y = 680; y <= 715; y += 3) {{
                    if (getR(x, y) > 215 && getB(x, y) < 120) spinner++;
                }}
            }}
            if (spinner >= 3) {{
                cfg.put("white_count", 0);
                return handleLoadingWait(cfg, "loading_count", "PIN_SPINNER", 9, 40, cid, adminId);
            }}
            cfg.put("last_state", "PIN_PAD");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            String stepText = prepareStepStatus(cfg, cid, adminId, "🔐 Entering PIN...", 50);
            queueStepStatus(cfg, stepText);
            saveConfig(cfg);
            return "ENTER_PIN";
        }}
    }}

    // 8. Check Telcell Dashboard (navigate via Услуги -> Транспорт)
    boolean dashNav = isOrange(360, 1372) || (isWhite(50, 1490) && isWhite(670, 1490) && getB(80, 1430) - getG(80, 1430) > 30);
    if (dashNav) {{
        cfg.put("vm_booting", false);
        if (mode.equals("reset") && resetStage == 0) {{
            return handleResetInApp(cfg, cid, adminId);
        }}
        if (isWhite(200, 300) && isWhite(580, 415) && isWhite(360, 800)) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 9, 50, cid, adminId);
        }}
        int svcLow = 0;
        int svcHigh = 0;
        for (int x = 50; x <= 340; x += 8) {{
            if (x > 110 && x < 280) continue;
            for (int y = 1045; y <= 1105; y += 6) {{
                if (getR(x, y) > 200 && getG(x, y) >= 70 && getG(x, y) <= 165 && getB(x, y) < 125) svcLow++;
            }}
            for (int y = 785; y <= 845; y += 6) {{
                if (getR(x, y) > 200 && getG(x, y) >= 70 && getG(x, y) <= 165 && getB(x, y) < 125) svcHigh++;
            }}
        }}
        if (svcLow < 3 && svcHigh < 3 && cfg.optInt("loading_count", 0) < 5) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 9, 50, cid, adminId);
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        boolean useLow = (svcLow >= 3) || (svcHigh < 3 && isWhite(360, 1100) && !isWhite(360, 800));
        cfg.put("last_state", useLow ? "DASHBOARD_LOW" : "DASHBOARD_HIGH");
        String stepText = prepareStepStatus(cfg, cid, adminId, "📲 Opening Transport tickets...", 60);
        queueStepStatus(cfg, stepText);
        saveConfig(cfg);
        return useLow ? "CLICK_TRANSPORT_LOW" : "CLICK_TRANSPORT_HIGH";
    }}

    // 9. Check Telcell Ticket List (Проездной билет -> Доступно)
    boolean buyBtnOrange = (isOrange(360, 1420) && isOrange(200, 1420)) || (isOrange(360, 1455) && isOrange(200, 1455));
    boolean availTabOrange = isOrange(277, 235) && isWhite(100, 235);
    boolean ticketBgGray = getR(360, 800) >= 240 && getR(360, 800) <= 250 && getG(360, 800) >= 240 && getG(360, 800) <= 251;
    if ((buyBtnOrange || availTabOrange) && ticketBgGray) {{
        cfg.put("vm_booting", false);
        if (mode.equals("reset") && resetStage == 0) {{
            return handleResetInApp(cfg, cid, adminId);
        }}
        if (getR(360, 400) < 252 || getG(360, 400) < 252 || getB(360, 400) < 252) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "TICKET_LOADING", 9, 70, cid, adminId);
        }}
        if (mode.equals("reset")) {{
            long popNextCid = 0L;
            long popNextMid = 0L;
            boolean hasNext = false;
            synchronized (System.class) {{
                JSONObject latestCfg = loadConfig();
                JSONArray queue = latestCfg.optJSONArray("queue");
                cfg.put("qr_was_closed", true);
                cfg.put("other_count", 0);
                resetWaitCounters(cfg);
                long nowMs = System.currentTimeMillis();
                if (queue != null && queue.length() > 0) {{
                    JSONObject nextItem = queue.getJSONObject(0);
                    JSONArray rem = new JSONArray();
                    for (int qi = 1; qi < queue.length(); qi++) {{
                        rem.put(queue.get(qi));
                    }}
                    popNextCid = nextItem.optLong("chat_id", 0L);
                    popNextMid = nextItem.optLong("status_message_id", 0L);
                    long prevStart = latestCfg.optLong("run_start_ms", cfg.optLong("run_start_ms", 0L));
                    long nextRunStart = (nowMs > prevStart) ? nowMs : (prevStart + 1L);
                    cfg.put("_pop_queue", true);
                    cfg.put("queue", rem);
                    cfg.put("capture_mode", "qr");
                    cfg.put("active_chat_id", popNextCid);
                    cfg.put("status_message_id", popNextMid);
                    cfg.put("run_start_ms", nextRunStart);
                    cfg.put("step_count", 2);
                    cfg.put("reset_stage", 0);
                    cfg.put("reset_kills", 0);
                    cfg.put("reset_recents_checked", false);
                    cfg.put("reset_open_tries", 0);
                    cfg.put("reset_notified", false);
                    cfg.put("busy_until", nowMs + 45000L);
                    cfg.put("worker_heartbeat_ms", nowMs);
                    cfg.put("last_state", "TICKET_LIST");
                    cfg.put("progress_pct", (popNextCid == adminId) ? 0 : 80);
                    String nextText = (popNextCid == adminId)
                        ? "🎫 Selecting ticket..."
                        : formatProgress("⏳ Generating QR code...", 80);
                    queueStepStatus(cfg, nextText);
                    saveConfig(cfg);
                    hasNext = true;
                }} else {{
                    queueStepStatus(cfg, null);
                }}
            }}
            if (hasNext) {{
                updateStatus(cid, statusMsgId, "✅ VM app reset complete — Telcell restarted & ready.");
                return "CLICK_TICKET_ROW";
            }}
            updateStatus(cid, statusMsgId, "✅ VM app reset complete — Telcell restarted & ready.");
            synchronized (System.class) {{
                long nowMs = System.currentTimeMillis();
                cfg.put("_pop_queue", true);
                cfg.put("queue", new JSONArray());
                cfg.put("last_state", "RESET");
                cfg.put("reset_notified", true);
                cfg.put("busy_until", 0L);
                cfg.put("worker_active", false);
                cfg.put("worker_pending_start_ms", 0L);
                cfg.put("worker_exiting_ms", nowMs);
                cfg.put("worker_heartbeat_ms", nowMs);
                saveConfig(cfg);
            }}
            return "DONE_RESET";
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("last_state", "TICKET_LIST");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        String stepText = prepareStepStatus(cfg, cid, adminId, "🎫 Selecting ticket...", 80);
        queueStepStatus(cfg, stepText);
        saveConfig(cfg);
        return "CLICK_TICKET_ROW";
    }}

    // 9b. Check Telcell Buy Ticket Tab (Проездной билет -> Купить билет)
    boolean buyTabOrange = isOrange(100, 235) && isWhite(277, 235);
    boolean buyCardBtns = isWhite(360, 120) && isWhite(277, 235) && isOrange(550, 485);
    if (buyTabOrange || buyCardBtns) {{
        cfg.put("vm_booting", false);
        if (mode.equals("reset") && resetStage == 0) {{
            return handleResetInApp(cfg, cid, adminId);
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("last_state", "BUY_TICKET_TAB");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        String stepText = prepareStepStatus(cfg, cid, adminId, "🎫 Switching to Available tickets...", 70);
        queueStepStatus(cfg, stepText);
        saveConfig(cfg);
        return "CLICK_AVAILABLE_TAB";
    }}

    // 10. Check pure white loading screen (multi-column grid avoids dense UI screens)
    if (isWhite(360, 240) && isWhite(360, 800) && isWhite(550, 485)) {{
        int whiteHits = 0;
        for (int x = 120; x <= 600; x += 120) {{
            for (int y = 240; y <= 1290; y += 150) {{
                if (isWhite(x, y)) whiteHits++;
            }}
        }}
        if (whiteHits >= 34) {{
            cfg.put("loading_count", 0);
            int maxWhite = (vmBooting || mode.equals("reset")) ? 18 : 7;
            return handleLoadingWait(cfg, "white_count", "WHITE_LOADING", maxWhite, 40, cid, adminId);
        }}
    }}

    // 11. Unknown / transition screen
    int otherCount = cfg.optInt("other_count", 0) + 1;
    cfg.put("other_count", otherCount);
    cfg.put("last_state", "OTHER");
    resetWaitCounters(cfg);
    queueStepStatus(cfg, null);
    saveConfig(cfg);
    if (vmBooting) {{
        if (otherCount <= 30) {{
            return "WAIT";
        }}
        if (otherCount == 31) {{
            return "CLICK_BACK";
        }}
        cfg.put("other_count", 0);
        saveConfig(cfg);
        return "RESET_TO_HOME";
    }}
    if (otherCount <= 2 || otherCount == 4) {{
        return "WAIT";
    }}
    if (otherCount == 3) {{
        return "CLICK_BACK";
    }}
    cfg.put("other_count", 0);
    saveConfig(cfg);
    return "RESET_TO_HOME";
}} finally {{
    bmp.recycle();
    if (!deletedNow) cleanScreenshots(dirs, latest, latestName);
}}
"""
    )


def build_post_step_script() -> str:
    """BeanShell Java 7 script overlapping status edits with post-tap settle pause."""
    return (
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import org.json.JSONArray;\n"
        "import org.json.JSONObject;\n\n"
        'String botToken = "{lv=bot_token}".trim();\n'
        'String stepCmd = "{lv=step_cmd}".trim();\n'
        'String configPath = "/storage/emulated/0/Download/komobot_config.json";\n\n'
        + _BSH_READ_STREAM
        + "\n\n"
        + _BSH_TG_HTTP_HELPERS
        + "\n\n"
        + _BSH_WORKER_CONFIG_HELPERS
        + """

long t0 = System.currentTimeMillis();
long waitMs = 350L;
if (stepCmd.equals("WAIT")) waitMs = 300L;
else if (stepCmd.equals("DISMISS_POPUP")) waitMs = 350L;
else if (stepCmd.equals("CLOSE_MODAL") || stepCmd.equals("CLICK_BACK") || stepCmd.equals("RESET_TO_HOME")) waitMs = 450L;
else if (stepCmd.equals("OPEN_RECENTS") || stepCmd.equals("SWIPE_KILL_RECENT")) waitMs = 550L;
else if (stepCmd.equals("CLICK_TICKET_ROW")) waitMs = 600L;
else if (stepCmd.equals("CLICK_AVAILABLE_TAB")) waitMs = 700L;
else if (stepCmd.equals("CLICK_TRANSPORT_LOW") || stepCmd.equals("CLICK_TRANSPORT_HIGH")) waitMs = 750L;
else if (stepCmd.equals("CLICK_ENTER")) waitMs = 900L;
else if (stepCmd.equals("ENTER_PIN")) waitMs = 1000L;
else if (stepCmd.equals("LAUNCH_1") || stepCmd.equals("LAUNCH_2")) waitMs = 1100L;

long cid = 0L;
long mid = 0L;
String pendingText = "";
synchronized (System.class) {
    JSONObject cfg = loadConfig();
    if (cfg.has("active_chat_id") || cfg.optBoolean("worker_active", false)) {
        cfg.put("worker_heartbeat_ms", System.currentTimeMillis());
        pendingText = cfg.optString("pending_status_text", "");
        if (pendingText.length() > 0) {
            cid = cfg.optLong("active_chat_id", 0L);
            mid = cfg.optLong("status_message_id", 0L);
            if (mid > 0L) {
                cfg.put("pending_status_text", "");
            }
        }
        saveConfig(cfg);
    }
}
if (pendingText.length() > 0 && mid > 0L) {
    updateStatus(cid, mid, pendingText);
}

long rem = waitMs - (System.currentTimeMillis() - t0);
if (rem > 0L) {
    try {
        Thread.sleep(rem);
    } catch (Exception e) {
    }
}
return "OK";
"""
    )


def build_timeout_script() -> str:
    """BeanShell Java 7 post-loop guard to clear busy lock and report timeouts."""
    return (
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import org.json.JSONArray;\n"
        "import org.json.JSONObject;\n\n"
        'String botToken = "{lv=bot_token}".trim();\n'
        'String configPath = "/storage/emulated/0/Download/komobot_config.json";\n'
        'String stepCmd = "{lv=step_cmd}".trim();\n\n'
        + _BSH_READ_STREAM
        + "\n\n"
        + _BSH_FRAME_HELPER
        + "\n\n"
        + _BSH_TG_HTTP_HELPERS
        + """

if (stepCmd.equals("ABORT_PREEMPTED")) return "KEEP_ON";

boolean keepScreenOn = false;
boolean notifyCleanup = false;
boolean resetAlreadyNotified = false;
long adminId = 0L;
long cid = 0L;
long mid = 0L;
String lastState = "UNKNOWN";
int stepCount = 0;
JSONArray queue = null;

synchronized (System.class) {
    File f = new File(configPath);
    if (f.exists()) {
        FileInputStream fis = new FileInputStream(f);
        String raw = readStream(fis);
        fis.close();
        if (raw.length() > 0) {
            JSONObject cfg = new JSONObject(raw);
            adminId = cfg.optLong("admin_id", 0L);
            long busyUntil = cfg.optLong("busy_until", 0L);
            boolean workerActive = cfg.optBoolean("worker_active", false);
            resetAlreadyNotified = cfg.optBoolean("reset_notified", false);
            cid = cfg.optLong("active_chat_id", 0L);
            mid = cfg.optLong("status_message_id", 0L);
            lastState = cfg.optString("last_state", "UNKNOWN");
            stepCount = cfg.optInt("step_count", 0);

            boolean newRunClaimed = (
                stepCmd.equals("DONE") && (workerActive || busyUntil > 0L)
            ) || (
                stepCmd.equals("DONE_RESET")
                && resetAlreadyNotified
                && (workerActive || busyUntil > 0L)
            );
            if (newRunClaimed) {
                keepScreenOn = true;
            } else {
                boolean dirty = false;
                if (cfg.optBoolean("worker_active", false)
                    || cfg.optLong("worker_pending_start_ms", 0L) > 0L
                    || cfg.optLong("worker_exiting_ms", 0L) > 0L) {
                    cfg.put("worker_active", false);
                    cfg.put("worker_pending_start_ms", 0L);
                    cfg.put("worker_exiting_ms", 0L);
                    dirty = true;
                }
                if (stepCmd.equals("DONE")) {
                    // Already completed QR flow; only clear worker flags
                } else if (busyUntil > 0L || (stepCmd.equals("DONE_RESET") && !resetAlreadyNotified)) {
                    queue = cfg.optJSONArray("queue");
                    cfg.put("busy_until", 0L);
                    cfg.put("queue", new JSONArray());
                    cfg.put("pending_status_text", "");
                    dirty = true;
                    notifyCleanup = true;
                }
                if (dirty) {
                    FileOutputStream fos = new FileOutputStream(f);
                    OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
                    osw.write(cfg.toString(2));
                    osw.flush();
                    osw.close();
                }
            }
        }
    }
}

if (keepScreenOn) {
    return "KEEP_ON";
}

deletePrivateFrames();

if (notifyCleanup) {
    String msg = stepCmd.equals("DONE_RESET")
        ? "✅ VM app reset complete — Telcell restarted & ready."
        : (cid == adminId
            ? "❌ Timed out waiting for QR screen (last state: " + lastState + "). Please try again."
            : "❌ Timed out generating QR code. Please try again.");
    updateStatus(cid, mid, msg);

    String failedQueueIds = "";
    if (queue != null) {
        String qMsg = stepCmd.equals("DONE_RESET")
            ? "❌ Request cancelled by VM reset. Please try again."
            : "❌ Previous request timed out. Please try again.";
        for (int qi = 0; qi < queue.length(); qi++) {
            JSONObject qItem = queue.optJSONObject(qi);
            if (qItem != null) {
                long qCid = qItem.optLong("chat_id", 0L);
                updateStatus(qCid, qItem.optLong("status_message_id", 0L), qMsg);
                if (!stepCmd.equals("DONE_RESET") && qCid != adminId && qCid > 0L) {
                    if (failedQueueIds.length() > 0) {
                        failedQueueIds = failedQueueIds + ", ";
                    }
                    failedQueueIds = failedQueueIds + qCid;
                }
            }
        }
    }

    if (!stepCmd.equals("DONE_RESET") && adminId > 0L) {
        if (cid != adminId && cid > 0L) {
            String adminNotice = "⚠️ User request failed (chat_id: " + cid
                + ")\\nReason: Timed out waiting for QR screen\\nLast state: " + lastState
                + " (step " + stepCount + ")";
            if (failedQueueIds.length() > 0) {
                adminNotice = adminNotice + "\\nAffected queued users: " + failedQueueIds;
            }
            sendMsg(adminId, adminNotice, null);
        } else if (failedQueueIds.length() > 0) {
            sendMsg(adminId,
                "⚠️ Queued user request(s) failed due to timeout: " + failedQueueIds
                + "\\nLast state: " + lastState + " (step " + stepCount + ")",
                null);
        }
    }
}
return "SCREEN_OFF";
"""
    )


def build_macro(
    bot_token_var: str = "",
    admin_id_var: str = "",
    app_pin_var: str = "",
    app_name_var: str = "",
) -> dict:
    """Assemble the full MacroDroid macro JSON structure."""
    sg = SiguidGen("komobot-v2")
    actions: list[dict] = []

    # 1. Extract update_id, chat_id, msg_text safely from webhook_body
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"update_id":0',
            '"update_id":\\s*(\\d+)',
            "update_id",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"chat":{"id":0',
            '"chat":\\s*\\{\\s*"id":\\s*(-?\\d+)',
            "chat_id",
        )
    )
    actions.append(
        make_extract_text(
            sg, '{lv=webhook_body}\n"text":""', r'"text":\s*"([^"]{0,200})"', "msg_text"
        )
    )

    # 2. JavaAction #1: Telegram Router, Auth & Command Handler
    actions.append(
        make_java_action(sg, build_router_script(), response_var="bot_action")
    )

    # 3. If bot_action == "RUN": wake screen and launch VM immediately, overlapping initial status send
    actions.append(make_if_var_equals(sg, "bot_action", "RUN"))
    actions.append(make_screen_on(sg, screen_off=False))
    actions.append(
        make_launch_app(sg, "Virtual Master", "com.clone.android.dual.space")
    )
    actions.append(make_java_action(sg, build_init_status_script()))

    # 4. Vision state loop (up to 95 total steps across preempted/queued requests; per-request cap = 45)
    actions.append(make_loop(sg, 130))
    actions.append(make_take_screenshot(sg))
    actions.append(make_java_action(sg, build_vision_script(), response_var="step_cmd"))

    def add_cmd_branch(cmd: str, branch_actions: list[dict]) -> None:
        actions.append(make_if_var_equals(sg, "step_cmd", cmd))
        actions.extend(branch_actions)
        actions.append(make_end_if(sg))

    # Close QR modal only on DONE; DONE_RESET keeps freshly restarted Telcell parked on Ticket List
    add_cmd_branch(
        "DONE",
        [make_click_xy(sg, 626, 121), make_pause(sg, millis=250), make_break_loop(sg)],
    )
    add_cmd_branch("DONE_RESET", [make_break_loop(sg)])
    add_cmd_branch("ABORT_PREEMPTED", [make_break_loop(sg)])
    add_cmd_branch("ABORT_TIMEOUT", [make_break_loop(sg)])
    add_cmd_branch("CLICK_ENTER", [make_click_xy(sg, 627, 250)])
    add_cmd_branch("DISMISS_POPUP", [make_click_xy(sg, 100, 200)])
    add_cmd_branch("OPEN_RECENTS", [make_click_xy(sg, 567, 1553)])
    add_cmd_branch(
        "SWIPE_KILL_RECENT", [make_gesture_swipe(sg, 360, 900, 360, 200, 200)]
    )
    add_cmd_branch("LAUNCH_1", [make_click_xy(sg, 97, 382)])
    add_cmd_branch("LAUNCH_2", [make_click_xy(sg, 97, 142)])

    pin_actions: list[dict] = [
        make_extract_text(sg, "{lv=app_pin}", "^(\\d)", "pin_d1"),
        make_extract_text(sg, "{lv=app_pin}", "^\\d(\\d)", "pin_d2"),
        make_extract_text(sg, "{lv=app_pin}", "^\\d\\d(\\d)", "pin_d3"),
        make_extract_text(sg, "{lv=app_pin}", "^\\d\\d\\d(\\d)", "pin_d4"),
    ]
    pin_vars = ("pin_d1", "pin_d2", "pin_d3", "pin_d4")
    for idx, d_var in enumerate(pin_vars):
        for digit in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
            px, py = PIN_COORDS[digit]
            pin_actions.append(make_if_var_equals(sg, d_var, digit))
            pin_actions.append(make_click_xy(sg, px, py))
            pin_actions.append(make_end_if(sg))
        if idx < len(pin_vars) - 1:
            pin_actions.append(make_pause(sg, millis=400))
    add_cmd_branch("ENTER_PIN", pin_actions)

    add_cmd_branch("CLICK_TRANSPORT_LOW", [make_click_xy(sg, 360, 1100)])
    add_cmd_branch("CLICK_TRANSPORT_HIGH", [make_click_xy(sg, 360, 840)])
    add_cmd_branch("CLICK_AVAILABLE_TAB", [make_click_xy(sg, 277, 200)])
    add_cmd_branch("CLICK_TICKET_ROW", [make_click_xy(sg, 360, 400)])
    add_cmd_branch("CLOSE_MODAL", [make_click_xy(sg, 626, 121)])
    add_cmd_branch("CLICK_BACK", [make_click_xy(sg, 151, 1553)])
    add_cmd_branch("RESET_TO_HOME", [make_click_xy(sg, 360, 1553)])
    add_cmd_branch("WAIT", [make_pause(sg, millis=50)])

    actions.append(make_java_action(sg, build_post_step_script()))
    actions.append(make_end_loop(sg))

    # 5. Post-loop timeout & reset completion guard
    actions.append(
        make_java_action(sg, build_timeout_script(), response_var="screen_action")
    )

    # 6. Turn screen off without leaving Virtual Master (skip if a newer worker/request owns the screen)
    actions.append(make_if_var_equals(sg, "screen_action", "SCREEN_OFF"))
    actions.append(make_screen_on(sg, screen_off=True))
    actions.append(make_end_if(sg))
    actions.append(make_end_if(sg))

    local_vars = [
        make_var("admin_id", value=admin_id_var, supports_input=True),
        make_var("app_name", value=app_name_var, supports_input=True),
        make_var("app_pin", value=app_pin_var, supports_input=True),
        make_var("bot_action"),
        make_var("bot_token", value=bot_token_var, supports_input=True),
        make_var("chat_id", supports_input=False),
        make_var("msg_text", supports_input=False),
        make_var("pin_d1", supports_input=False),
        make_var("pin_d2", supports_input=False),
        make_var("pin_d3", supports_input=False),
        make_var("pin_d4", supports_input=False),
        make_var("screen_action"),
        make_var("step_cmd"),
        make_var("update_id", supports_input=False),
        make_var("webhook_body", working=True, supports_input=False),
    ]

    return {
        "globalVariables": [],
        "macro": {
            "aiGenerated": 0,
            "breakpoints": [],
            "disabledTimestamp": 0,
            "exportedActionBlocks": [],
            "exportedSharedScenes": [],
            "forceEvenIfNotEnabledTimestamp": 0,
            "isActionBlock": False,
            "isExtra": False,
            "isFavourite": False,
            "lastEditedTimestamp": 1794664000000,
            "localVariableSeparators": [],
            "localVariables": local_vars,
            "localVarsAlphabetical": True,
            "loggingLevel": 0,
            "m_GUID": -6036074823323852000,
            "m_actionList": actions,
            "m_category": "Uncategorized",
            "m_completed": True,
            "m_constraintList": [],
            "m_description": (
                "Automated Komobot Telegram + Virtual Master QR Controller"
            ),
            "m_descriptionOpen": False,
            "m_enabled": True,
            "m_excludeLog": False,
            "m_headingColor": 0,
            "m_isOrCondition": False,
            "m_name": "Komobot Controller",
            "m_triggerList": [
                {
                    "identifier": "komobotv2",
                    "ipAddressWhiteList": [],
                    "saveBodyVariableName": "webhook_body",
                    "variableWhiteList": [],
                    "variableWhiteListEnabled": False,
                    "disableLogging": False,
                    "m_SIGUID": -7390523152389324000,
                    "m_classType": "WebHookTrigger",
                    "m_comment": "",
                    "m_constraintList": [],
                    "m_isDisabled": False,
                    "m_isOrCondition": False,
                }
            ],
        },
        "macroExportVersion": 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Komobot MacroDroid files.")
    parser.add_argument(
        "--bot-token",
        default="",
        help="Telegram bot token for MacroDroid bot_token variable",
    )
    parser.add_argument(
        "--admin-id",
        default="",
        help="Telegram admin ID for MacroDroid admin_id variable",
    )
    parser.add_argument(
        "--app-pin", default="", help="App PIN for MacroDroid app_pin variable"
    )
    parser.add_argument(
        "--app-name",
        default="",
        help="Target app package for MacroDroid app_name variable",
    )
    args = parser.parse_args()

    deploy_data = build_macro(
        bot_token_var=args.bot_token,
        admin_id_var=args.admin_id,
        app_pin_var=args.app_pin,
        app_name_var=args.app_name,
    )
    OUT_MACRO.write_text(
        json.dumps(deploy_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    action_count = len(deploy_data["macro"]["m_actionList"])
    print(f"Generated {OUT_MACRO.name} ({action_count} actions)")


if __name__ == "__main__":
    main()
