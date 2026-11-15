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


def make_if_var_equals(sg: SiguidGen, var_name: str, expected: str) -> dict:
    """Build an IfConditionAction checking string equality on a local variable."""
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
                "m_stringEqual": True,
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


def make_click_xy(sg: SiguidGen, x: int, y: int) -> dict:
    return {
        "action": 0,
        "uiInteractionConfiguration": {
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
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "UIInteractionAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_click_text(sg: SiguidGen, text: str, blocking: bool = False) -> dict:
    return {
        "action": 0,
        "uiInteractionConfiguration": {
            "blocking": blocking,
            "checkOverlays": False,
            "clickOption": 1,
            "contextClick": False,
            "longClick": False,
            "showTouchLocation": False,
            "skipCount": "0",
            "textContent": text,
            "textMatchOption": 0,
            "useRegex": False,
            "xyPercentages": False,
            "xyPoint": {"x": 0, "y": 0},
            "type": "Click",
        },
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "UIInteractionAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


def make_take_screenshot(sg: SiguidGen) -> dict:
    return {
        "emailSubject": "Screenshot",
        "m_mechanismOption": 0,
        "m_option": 0,
        "saveToJpeg": False,
        "screenshotFormat": 0,
        "uiOption": 0,
        "useCustomFilename": False,
        "useCustomSaveLocation": False,
        "useSmtpEmail": False,
        "disableLogging": False,
        "m_SIGUID": sg.next_id(),
        "m_classType": "TakeScreenshotAction",
        "m_comment": "",
        "m_constraintList": [],
        "m_isDisabled": False,
        "m_isOrCondition": False,
    }


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

String readStream(InputStream is) throws Exception {{
    if (is == null) return "";
    BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) {{
        sb.append(line);
    }}
    br.close();
    return sb.toString();
}}

JSONObject tgPost(String method, JSONObject payload) {{
    HttpURLConnection conn = null;
    try {{
        URL url = new URL("https://api.telegram.org/bot" + botToken + "/" + method);
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        byte[] outBytes = payload.toString().getBytes("UTF-8");
        OutputStream os = conn.getOutputStream();
        os.write(outBytes);
        os.flush();
        os.close();
        int code = conn.getResponseCode();
        InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();
        String resp = readStream(is);
        if (resp.length() > 0) {{
            return new JSONObject(resp);
        }}
    }} catch (Exception e) {{
    }} finally {{
        if (conn != null) conn.disconnect();
    }}
    return new JSONObject();
}}

JSONObject sendMsg(long cid, String text, JSONObject markup) {{
    try {{
        JSONObject body = new JSONObject();
        body.put("chat_id", cid);
        body.put("text", text);
        if (markup != null) {{
            body.put("reply_markup", markup);
        }}
        return tgPost("sendMessage", body);
    }} catch (Exception e) {{
        return new JSONObject();
    }}
}}

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
long claimedRunStart = 0L;
int qPos = 0;
boolean dupUid = false;

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
        JSONArray allowed = cfg.optJSONArray("allowed_users");
        if (allowed == null) {{
            allowed = new JSONArray();
            allowed.put(adminId);
            cfg.put("allowed_users", allowed);
        }}

        boolean isAdmin = (cid == adminId);
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
                if (now < busyUntil) {{
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
                    String mode = "";
                    String lowerMsg = msgText.toLowerCase();
                    if (isAdmin && msgText.indexOf("Reset VM") >= 0) {{
                        mode = "reset";
                    }} else if (lowerMsg.equals("/qr") || lowerMsg.equals("qr") || msgText.indexOf("Take QR Screenshot") >= 0 || lowerMsg.indexOf("qr") >= 0 || lowerMsg.indexOf("screenshot") >= 0) {{
                        mode = "qr";
                    }}
                    if (mode.length() == 0) {{
                        saveConfig(cfg);
                    }} else {{
                        claimedRunStart = now;
                        cfg.put("busy_until", now + 45000L);
                        cfg.put("active_chat_id", cid);
                        cfg.put("app_name", appName);
                        cfg.put("capture_mode", mode);
                        cfg.put("queue", new JSONArray());
                        cfg.put("qr_was_closed", false);
                        cfg.put("step_count", 0);
                        cfg.put("other_count", 0);
                        cfg.put("white_count", 0);
                        cfg.put("loading_count", 0);
                        cfg.put("last_state", "INIT");
                        cfg.put("run_start_ms", now);
                        cfg.put("status_message_id", 0L);
                        saveConfig(cfg);
                        statusStage = "RUN";
                        actionResult = "RUN";
                    }}
                }}
            }}
        }}
    }}
}}

if (dupUid) {{
    return "IGNORE";
}}
if (replyText != null) {{
    sendMsg(cid, replyText, replyMarkup);
}} else if (statusStage.equals("QUEUE")) {{
    JSONObject qSent = sendMsg(cid, "⏳ Queued (#" + qPos + ") — waiting for current request to finish...", null);
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
}} else if (statusStage.equals("RUN")) {{
    JSONObject sent = sendMsg(cid, "🔍 Waking phone & checking Virtual Master...", null);
    long statusMsgId = sent.has("result") ? sent.getJSONObject("result").optLong("message_id", 0L) : 0L;
    if (statusMsgId > 0L) {{
        synchronized (System.class) {{
            JSONObject fresh = loadConfig();
            if (fresh.optLong("active_chat_id", 0L) == cid && fresh.optLong("run_start_ms", 0L) == claimedRunStart) {{
                fresh.put("status_message_id", statusMsgId);
                saveConfig(fresh);
            }}
        }}
    }}
}}
return actionResult;
"""


def build_vision_script() -> str:
    """BeanShell Java 7 script for screenshot polling, state machine & QR crop."""
    return f"""import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONArray;
import org.json.JSONObject;

String botToken = "{{lv=bot_token}}".trim();
String appName = "{{lv=app_name}}".trim();
String configPath = "/storage/emulated/0/Download/komobot_config.json";

String readStream(InputStream is) throws Exception {{
    if (is == null) return "";
    BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) {{
        sb.append(line);
    }}
    br.close();
    return sb.toString();
}}

JSONObject loadConfig() {{
    File f = new File(configPath);
    if (f.exists()) {{
        try {{
            FileInputStream fis = new FileInputStream(f);
            String raw = readStream(fis);
            fis.close();
            if (raw.length() > 0) return new JSONObject(raw);
        }} catch (Exception e) {{
        }}
    }}
    return new JSONObject();
}}

void saveConfig(JSONObject cfg) {{
    try {{
        synchronized (System.class) {{
            JSONObject fresh = loadConfig();
            if (!cfg.optBoolean("_pop_queue", false)) {{
                if (fresh.has("queue")) {{
                    cfg.put("queue", fresh.getJSONArray("queue"));
                }}
                if (fresh.optLong("busy_until", 0L) > cfg.optLong("busy_until", 0L) && cfg.optLong("busy_until", 0L) > 0L) {{
                    cfg.put("busy_until", fresh.optLong("busy_until", 0L));
                }}
            }}
            cfg.remove("_pop_queue");
            if (fresh.optLong("last_update_id", 0L) > cfg.optLong("last_update_id", 0L)) {{
                cfg.put("last_update_id", fresh.optLong("last_update_id", 0L));
            }}
            if (fresh.optLong("status_message_id", 0L) > 0L && cfg.optLong("status_message_id", 0L) == 0L &&
                fresh.optLong("active_chat_id", 0L) == cfg.optLong("active_chat_id", 0L) &&
                fresh.optLong("run_start_ms", 0L) == cfg.optLong("run_start_ms", 0L)) {{
                cfg.put("status_message_id", fresh.optLong("status_message_id", 0L));
            }}
            if (fresh.has("allowed_users")) {{
                cfg.put("allowed_users", fresh.getJSONArray("allowed_users"));
            }}
            if (fresh.has("public_access")) {{
                cfg.put("public_access", fresh.optBoolean("public_access", true));
            }}
            FileOutputStream fos = new FileOutputStream(new File(configPath));
            OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
            osw.write(cfg.toString(2));
            osw.flush();
            osw.close();
        }}
    }} catch (Exception e) {{
    }}
}}

void tgJson(String method, JSONObject payload) {{
    HttpURLConnection conn = null;
    try {{
        URL url = new URL("https://api.telegram.org/bot" + botToken + "/" + method);
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(6000);
        conn.setReadTimeout(6000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        OutputStream os = conn.getOutputStream();
        os.write(payload.toString().getBytes("UTF-8"));
        os.flush();
        os.close();
        conn.getResponseCode();
    }} catch (Exception e) {{
    }} finally {{
        if (conn != null) conn.disconnect();
    }}
}}

void updateStatus(long cid, long mid, String text) {{
    if (cid <= 0L || mid <= 0L) return;
    try {{
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        payload.put("text", text);
        tgJson("editMessageText", payload);
    }} catch (Exception e) {{
    }}
}}

void deleteStatus(long cid, long mid) {{
    if (cid <= 0L || mid <= 0L) return;
    try {{
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        tgJson("deleteMessage", payload);
    }} catch (Exception e) {{
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
        return -1;
    }} finally {{
        if (conn != null) conn.disconnect();
    }}
}}

void cleanScreenshots(String[] dirs, File latestFile, String latestName, long mtime) {{
    long waitMs = 1000L - (System.currentTimeMillis() - mtime);
    if (waitMs > 0L) {{
        try {{
            Thread.sleep(waitMs);
        }} catch (Exception e) {{
        }}
    }}
    if (latestFile != null) {{
        try {{
            latestFile.delete();
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
}}

JSONObject cfg = loadConfig();
long cid = cfg.optLong("active_chat_id", 0L);
long statusMsgId = cfg.optLong("status_message_id", 0L);
String mode = cfg.optString("capture_mode", "qr");
int stepCount = cfg.optInt("step_count", 0) + 1;
cfg.put("step_count", stepCount);
long minLease = System.currentTimeMillis() + 30000L;
if (cfg.optLong("busy_until", 0L) < minLease) {{
    cfg.put("busy_until", minLease);
}}
long runStartMs = cfg.optLong("run_start_ms", System.currentTimeMillis() - 5000L);
String lastSsName = cfg.optString("last_ss_name", "");
long lastSsMtime = cfg.optLong("last_ss_mtime", 0L);

String[] dirs = new String[]{{
    "/storage/emulated/0/DCIM/Screenshots",
    "/storage/emulated/0/Pictures/Screenshots"
}};

long waitStart = System.currentTimeMillis();
File latest = null;
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
            if (f.isFile() && n.startsWith("Screenshot") && f.length() > 5000L) {{
                long lm = f.lastModified();
                if (lm >= runStartMs - 2500L && (!n.equals(lastSsName) || lm > lastSsMtime)) {{
                    if (cand == null || lm > cand.lastModified()) {{
                        cand = f;
                    }}
                }}
            }}
        }}
    }}
    if (cand != null) {{
        latest = cand;
        break;
    }}
    Thread.sleep(150L);
}}

if (latest == null) {{
    cfg.put("last_state", "NO_SCREENSHOT");
    saveConfig(cfg);
    return "WAIT";
}}

String latestName = latest.getName();
long latestMtime = latest.lastModified();
cfg.put("last_ss_name", latestName);
cfg.put("last_ss_mtime", latestMtime);

Bitmap bmp = null;
for (int attempt = 0; attempt < 5; attempt++) {{
    bmp = BitmapFactory.decodeFile(latest.getAbsolutePath());
    if (bmp != null) break;
    Thread.sleep(120L);
}}

if (bmp == null) {{
    cleanScreenshots(dirs, latest, latestName, latestMtime);
    cfg.put("last_state", "DECODE_ERR");
    saveConfig(cfg);
    return "WAIT";
}}

try {{
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
    void resetWaitCounters(JSONObject cfg) throws Exception {{
        cfg.put("white_count", 0);
        cfg.put("loading_count", 0);
    }}
    String handleLoadingWait(JSONObject cfg, String countKey, String stateName, int maxWaits) throws Exception {{
        int cnt = cfg.optInt(countKey, 0) + 1;
        cfg.put(countKey, cnt);
        cfg.put("last_state", stateName);
        if (cnt <= maxWaits) {{
            saveConfig(cfg);
            return "WAIT";
        }}
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
        if (enterMax > 120) {{
            cfg.put("last_state", "VM_LAUNCHER");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "🖥️ Entering Virtual Master...");
            return "CLICK_ENTER";
        }}
        cfg.put("last_state", "VM_LOADING");
        resetWaitCounters(cfg);
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
        saveConfig(cfg);
        return "DISMISS_POPUP";
    }}

    // 3. Handle Reset VM App mode
    if (mode.equals("reset")) {{
        cfg.put("last_state", "RESET");
        cfg.put("busy_until", 0L);
        resetWaitCounters(cfg);
        saveConfig(cfg);
        return "DONE_RESET";
    }}

    // 4. Check QR Code Modal
    if (getR(30, 400) < 110 && getG(30, 400) < 110 && getB(30, 400) < 110 &&
        isWhite(150, 400) && isWhite(570, 400) && isWhite(130, 590) && isWhite(590, 590)) {{
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
                saveConfig(cfg);
                updateStatus(cid, statusMsgId, "🔄 Refreshing stale QR screen...");
                return "CLOSE_MODAL";
            }}
            updateStatus(cid, statusMsgId, "📸 Cropping & sending QR...");
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
                updateStatus(cid, statusMsgId, "❌ Failed to upload QR (HTTP " + code + ").");
            }}
            long popNextCid = 0L;
            long popNextMid = 0L;
            boolean hasNext = false;
            synchronized (System.class) {{
                JSONObject latestCfg = loadConfig();
                JSONArray queue = latestCfg.optJSONArray("queue");
                if (queue != null && queue.length() > 0) {{
                    JSONObject nextItem = queue.getJSONObject(0);
                    JSONArray rem = new JSONArray();
                    for (int qi = 1; qi < queue.length(); qi++) {{
                        rem.put(queue.get(qi));
                    }}
                    popNextCid = nextItem.optLong("chat_id", 0L);
                    popNextMid = nextItem.optLong("status_message_id", 0L);
                    cfg.put("_pop_queue", true);
                    cfg.put("queue", rem);
                    cfg.put("active_chat_id", popNextCid);
                    cfg.put("status_message_id", popNextMid);
                    cfg.put("qr_was_closed", true);
                    cfg.put("step_count", 2);
                    cfg.put("other_count", 0);
                    resetWaitCounters(cfg);
                    cfg.put("busy_until", System.currentTimeMillis() + 45000L);
                    cfg.put("last_state", "NEXT_IN_QUEUE");
                    saveConfig(cfg);
                    hasNext = true;
                }} else {{
                    cfg.put("_pop_queue", true);
                    cfg.put("queue", new JSONArray());
                    cfg.put("last_state", "QR_SENT");
                    cfg.put("busy_until", 0L);
                    resetWaitCounters(cfg);
                    saveConfig(cfg);
                }}
            }}
            if (hasNext) {{
                updateStatus(popNextCid, popNextMid, "🔄 Generating QR code for your request...");
                return "CLOSE_MODAL";
            }} else {{
                return "DONE";
            }}
        }}
        cfg.put("white_count", 0);
        return handleLoadingWait(cfg, "loading_count", "QR_LOADING", 6);
    }}

    // 6. Check VM Home Screen (Telcell icon orange pixels)
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
        if (o1 >= 15) {{
            cfg.put("last_state", "VM_HOME_1");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "🚀 Launching Telcell Wallet...");
            return "LAUNCH_1";
        }}
        if (o2 >= 15) {{
            cfg.put("last_state", "VM_HOME_2");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "🚀 Launching Telcell Wallet...");
            return "LAUNCH_2";
        }}
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
            int spinner = 0;
            for (int x = 330; x <= 390; x += 3) {{
                for (int y = 680; y <= 715; y += 3) {{
                    if (getR(x, y) > 215 && getB(x, y) < 120) spinner++;
                }}
            }}
            if (spinner >= 3) {{
                cfg.put("white_count", 0);
                return handleLoadingWait(cfg, "loading_count", "PIN_SPINNER", 6);
            }}
            cfg.put("last_state", "PIN_PAD");
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "🔐 Entering PIN...");
            return "ENTER_PIN";
        }}
    }}

    // 8. Check Telcell Dashboard (navigate via Услуги -> Транспорт)
    boolean dashNav = isOrange(360, 1372) || (isWhite(50, 1490) && isWhite(670, 1490) && getB(80, 1430) - getG(80, 1430) > 30);
    if (dashNav) {{
        if (isWhite(200, 300) && isWhite(580, 415) && isWhite(360, 800)) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 6);
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
        if (svcLow < 3 && svcHigh < 3 && cfg.optInt("loading_count", 0) < 3) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 6);
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        if (svcLow >= 3) {{
            cfg.put("last_state", "DASHBOARD_LOW");
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "📲 Opening Transport tickets...");
            return "CLICK_TRANSPORT_LOW";
        }}
        if (svcHigh >= 3) {{
            cfg.put("last_state", "DASHBOARD_HIGH");
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "📲 Opening Transport tickets...");
            return "CLICK_TRANSPORT_HIGH";
        }}
        if (isWhite(360, 1100) && !isWhite(360, 800)) {{
            cfg.put("last_state", "DASHBOARD_LOW");
            saveConfig(cfg);
            updateStatus(cid, statusMsgId, "📲 Opening Transport tickets...");
            return "CLICK_TRANSPORT_LOW";
        }}
        cfg.put("last_state", "DASHBOARD_HIGH");
        saveConfig(cfg);
        updateStatus(cid, statusMsgId, "📲 Opening Transport tickets...");
        return "CLICK_TRANSPORT_HIGH";
    }}

    // 9. Check Telcell Ticket List (Проездной билет -> Доступно)
    boolean buyBtnOrange = (isOrange(360, 1420) && isOrange(200, 1420)) || (isOrange(360, 1455) && isOrange(200, 1455));
    boolean availTabOrange = isOrange(277, 235) && isWhite(100, 235);
    boolean ticketBgGray = getR(360, 800) >= 240 && getR(360, 800) <= 250 && getG(360, 800) >= 240 && getG(360, 800) <= 251;
    if ((buyBtnOrange || availTabOrange) && ticketBgGray) {{
        if (getR(360, 400) < 252 || getG(360, 400) < 252 || getB(360, 400) < 252) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "TICKET_LOADING", 6);
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("last_state", "TICKET_LIST");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        saveConfig(cfg);
        updateStatus(cid, statusMsgId, "🎫 Selecting ticket...");
        return "CLICK_TICKET_ROW";
    }}

    // 9b. Check Telcell Buy Ticket Tab (Проездной билет -> Купить билет)
    boolean buyTabOrange = isOrange(100, 235) && isWhite(277, 235);
    boolean buyCardBtns = isWhite(360, 120) && isWhite(277, 235) && isOrange(550, 485);
    if (buyTabOrange || buyCardBtns) {{
        cfg.put("qr_was_closed", true);
        cfg.put("last_state", "BUY_TICKET_TAB");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        saveConfig(cfg);
        updateStatus(cid, statusMsgId, "🎫 Switching to Available tickets...");
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
            return handleLoadingWait(cfg, "white_count", "WHITE_LOADING", 5);
        }}
    }}

    // 11. Unknown / transition screen
    int otherCount = cfg.optInt("other_count", 0) + 1;
    cfg.put("other_count", otherCount);
    cfg.put("last_state", "OTHER");
    resetWaitCounters(cfg);
    saveConfig(cfg);
    if (otherCount == 1 || otherCount == 3) {{
        return "WAIT";
    }}
    if (otherCount == 2) {{
        return "CLICK_BACK";
    }}
    cfg.put("other_count", 0);
    saveConfig(cfg);
    return "RESET_TO_HOME";
}} finally {{
    bmp.recycle();
    cleanScreenshots(dirs, latest, latestName, latestMtime);
}}
"""


def build_timeout_script() -> str:
    """BeanShell Java 7 post-loop guard to clear busy lock and report timeouts."""
    return f"""import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONArray;
import org.json.JSONObject;

String botToken = "{{lv=bot_token}}".trim();
String configPath = "/storage/emulated/0/Download/komobot_config.json";
String stepCmd = "{{lv=step_cmd}}".trim();

String readStream(InputStream is) throws Exception {{
    if (is == null) return "";
    BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) sb.append(line);
    br.close();
    return sb.toString();
}}

void editTgMsg(String token, long chatId, long msgId, String text) {{
    if (chatId <= 0L || msgId <= 0L) return;
    HttpURLConnection conn = null;
    try {{
        URL url = new URL("https://api.telegram.org/bot" + token + "/editMessageText");
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(6000);
        conn.setReadTimeout(6000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        JSONObject payload = new JSONObject();
        payload.put("chat_id", chatId);
        payload.put("message_id", msgId);
        payload.put("text", text);
        OutputStream os = conn.getOutputStream();
        os.write(payload.toString().getBytes("UTF-8"));
        os.flush();
        os.close();
        conn.getResponseCode();
    }} catch (Exception e) {{
    }} finally {{
        if (conn != null) conn.disconnect();
    }}
}}

File f = new File(configPath);
if (!f.exists()) return "OK";

FileInputStream fis = new FileInputStream(f);
String raw = readStream(fis);
fis.close();
if (raw.length() == 0) return "OK";

JSONObject cfg = new JSONObject(raw);
long busyUntil = cfg.optLong("busy_until", 0L);
long cid = cfg.optLong("active_chat_id", 0L);
long mid = cfg.optLong("status_message_id", 0L);
String lastState = cfg.optString("last_state", "UNKNOWN");

if (busyUntil > 0L || stepCmd.equals("DONE_RESET")) {{
    JSONArray queue = cfg.optJSONArray("queue");
    cfg.put("busy_until", 0L);
    cfg.put("queue", new JSONArray());
    FileOutputStream fos = new FileOutputStream(f);
    OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
    osw.write(cfg.toString(2));
    osw.flush();
    osw.close();

    String msg = stepCmd.equals("DONE_RESET")
        ? "✅ VM app reset complete."
        : "❌ Timed out waiting for QR screen (last state: " + lastState + "). Please try again.";
    editTgMsg(botToken, cid, mid, msg);

    if (queue != null) {{
        String qMsg = stepCmd.equals("DONE_RESET")
            ? "❌ Request cancelled by VM reset. Please try again."
            : "❌ Previous request timed out. Please try again.";
        for (int qi = 0; qi < queue.length(); qi++) {{
            JSONObject qItem = queue.optJSONObject(qi);
            if (qItem != null) {{
                editTgMsg(botToken, qItem.optLong("chat_id", 0L), qItem.optLong("status_message_id", 0L), qMsg);
            }}
        }}
    }}
}}
return "OK";
"""


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

    # 3. If bot_action == "RUN"
    actions.append(make_if_var_equals(sg, "bot_action", "RUN"))
    actions.append(make_screen_on(sg, screen_off=False))
    actions.append(
        make_launch_app(sg, "Virtual Master", "com.clone.android.dual.space")
    )
    actions.append(make_pause(sg, seconds=1, millis=200))

    # 4. Vision state loop (up to 32 iterations)
    actions.append(make_loop(sg, 32))
    actions.append(make_screen_on(sg, screen_off=False))
    actions.append(make_take_screenshot(sg))
    actions.append(make_java_action(sg, build_vision_script(), response_var="step_cmd"))

    def add_cmd_branch(cmd: str, branch_actions: list[dict]) -> None:
        actions.append(make_if_var_equals(sg, "step_cmd", cmd))
        actions.extend(branch_actions)
        actions.append(make_end_if(sg))

    add_cmd_branch(
        "DONE",
        [
            make_click_xy(sg, 626, 121),
            make_pause(sg, millis=500),
            make_click_xy(sg, 151, 1553),
            make_pause(sg, millis=500),
            make_click_xy(sg, 360, 1553),
            make_break_loop(sg),
        ],
    )
    add_cmd_branch(
        "DONE_RESET",
        [
            make_click_xy(sg, 626, 121),
            make_pause(sg, millis=300),
            make_click_xy(sg, 151, 1553),
            make_pause(sg, millis=300),
            make_click_xy(sg, 360, 1553),
            make_break_loop(sg),
        ],
    )
    add_cmd_branch(
        "CLICK_ENTER",
        [
            make_click_text(sg, "Enter", blocking=False),
            make_click_xy(sg, 627, 250),
            make_pause(sg, seconds=2),
        ],
    )
    add_cmd_branch(
        "DISMISS_POPUP", [make_click_xy(sg, 100, 200), make_pause(sg, millis=500)]
    )
    add_cmd_branch(
        "LAUNCH_1", [make_click_xy(sg, 97, 382), make_pause(sg, seconds=2, millis=500)]
    )
    add_cmd_branch(
        "LAUNCH_2", [make_click_xy(sg, 97, 142), make_pause(sg, seconds=2, millis=500)]
    )

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
            pin_actions.append(make_pause(sg, millis=450))
        else:
            pin_actions.append(make_pause(sg, seconds=2, millis=500))
    add_cmd_branch("ENTER_PIN", pin_actions)

    add_cmd_branch(
        "CLICK_TRANSPORT_LOW",
        [make_click_xy(sg, 360, 1100), make_pause(sg, seconds=1, millis=500)],
    )
    add_cmd_branch(
        "CLICK_TRANSPORT_HIGH",
        [make_click_xy(sg, 360, 840), make_pause(sg, seconds=1, millis=500)],
    )
    add_cmd_branch(
        "CLICK_AVAILABLE_TAB",
        [make_click_xy(sg, 277, 200), make_pause(sg, seconds=1, millis=500)],
    )
    add_cmd_branch(
        "CLICK_TICKET_ROW",
        [make_click_xy(sg, 360, 400), make_pause(sg, seconds=1, millis=200)],
    )
    add_cmd_branch(
        "CLOSE_MODAL", [make_click_xy(sg, 626, 121), make_pause(sg, millis=800)]
    )
    add_cmd_branch(
        "CLICK_BACK", [make_click_xy(sg, 151, 1553), make_pause(sg, millis=800)]
    )
    add_cmd_branch(
        "RESET_TO_HOME", [make_click_xy(sg, 360, 1553), make_pause(sg, millis=800)]
    )
    add_cmd_branch("WAIT", [make_pause(sg, seconds=1)])

    actions.append(make_end_loop(sg))

    # 5. Post-loop timeout & reset completion guard
    actions.append(make_java_action(sg, build_timeout_script()))

    # 6. Turn screen off without leaving Virtual Master (prevents VM backgrounding)
    actions.append(make_screen_on(sg, screen_off=True))
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
