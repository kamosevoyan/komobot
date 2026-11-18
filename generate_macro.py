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


_BSH_PROGRESS_HELPER = """String buildProgressBar(int pct) {
    int clamped = pct;
    if (clamped < 0) clamped = 0;
    if (clamped > 100) clamped = 100;
    int filled = clamped / 10;
    StringBuilder bar = new StringBuilder();
    for (int i = 0; i < 10; i++) {
        if (i < filled) {
            bar.append("🟩");
        } else {
            bar.append("⬜");
        }
    }
    return bar.toString() + " " + clamped + "%";
}

String formatProgress(String label, int pct) {
    return label + "\\n" + buildProgressBar(pct);
}

String formatButtonProgress(int pct) {
    return "⏳ " + buildProgressBar(pct);
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

_BSH_TG_HTTP_HELPERS = """JSONObject tgPostRaw(String method, JSONObject payload, int timeoutMs) {
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

JSONObject tgPost(String method, JSONObject payload, int timeoutMs) {
    return tgPostRaw(method, payload, timeoutMs);
}

void writeFormField(DataOutputStream req, String boundary, String name, String val) throws Exception {
    req.writeBytes("--" + boundary + "\\r\\n");
    req.writeBytes("Content-Disposition: form-data; name=\\"" + name + "\\"\\r\\n\\r\\n");
    req.write(val.getBytes("UTF-8"));
    req.writeBytes("\\r\\n");
}

JSONObject postMultipartRaw(String endpoint, long cid, long mid, JSONObject extraFields, String fileField, String filename, String mimeType, byte[] fileBytes, int timeoutMs) {
    JSONObject res = new JSONObject();
    res.put("code", -1);
    res.put("desc", "");
    HttpURLConnection conn = null;
    try {
        URL url = new URL("https://api.telegram.org/bot" + botToken + "/" + endpoint);
        conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(timeoutMs);
        conn.setReadTimeout(timeoutMs);
        conn.setDoOutput(true);
        String boundary = "*****" + System.currentTimeMillis() + "*****";
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        conn.setRequestProperty("Connection", "keep-alive");
        DataOutputStream req = new DataOutputStream(conn.getOutputStream());

        writeFormField(req, boundary, "chat_id", cid + "");
        if (mid > 0L) {
            writeFormField(req, boundary, "message_id", mid + "");
        }
        if (extraFields != null) {
            JSONArray keys = extraFields.names();
            if (keys != null) {
                for (int i = 0; i < keys.length(); i++) {
                    String k = keys.optString(i, "");
                    String v = extraFields.optString(k, "");
                    if (k.length() > 0 && v.length() > 0) {
                        writeFormField(req, boundary, k, v);
                    }
                }
            }
        }

        req.writeBytes("--" + boundary + "\\r\\n");
        req.writeBytes("Content-Disposition: form-data; name=\\"" + fileField + "\\"; filename=\\"" + filename + "\\"\\r\\n");
        req.writeBytes("Content-Type: " + mimeType + "\\r\\n\\r\\n");
        req.write(fileBytes);
        req.writeBytes("\\r\\n--" + boundary + "--\\r\\n");
        req.flush();
        req.close();

        int code = conn.getResponseCode();
        InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();
        String rawResp = readStream(is);
        res.put("code", code);
        if (rawResp.length() > 0) {
            try {
                JSONObject j = new JSONObject(rawResp);
                res.put("desc", j.optString("description", ""));
            } catch (Exception ignored) {
            }
        }
        return res;
    } catch (Exception e) {
        res.put("desc", e + "");
        if (conn != null) {
            try {
                conn.disconnect();
            } catch (Exception ignored) {
            }
        }
        return res;
    }
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

void editMsg(long cid, long mid, String text, JSONObject markup) {
    if (cid <= 0L || mid <= 0L || text == null || text.length() == 0) return;
    try {
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        payload.put("text", text);
        if (markup != null) {
            payload.put("reply_markup", markup);
        }
        tgPost("editMessageText", payload, 5000);
    } catch (Exception e) {
    }
}

void updateStatus(long cid, long mid, String text) {
    editMsg(cid, mid, text, null);
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
}

void answerCallback(String cbId, String text) {
    if (cbId == null || cbId.length() == 0) return;
    try {
        JSONObject payload = new JSONObject();
        payload.put("callback_query_id", cbId);
        if (text != null && text.length() > 0) {
            payload.put("text", text);
        }
        tgPost("answerCallbackQuery", payload, 2500);
    } catch (Exception e) {
    }
}

JSONObject makeBtn(String btnText, String cbData) {
    JSONObject btn = new JSONObject();
    btn.put("text", btnText);
    btn.put("callback_data", cbData);
    return btn;
}

JSONObject makeInlineButtonMarkup(String btnText, String cbData) {
    JSONArray row = new JSONArray();
    row.put(makeBtn(btnText, cbData));
    JSONArray kb = new JSONArray();
    kb.put(row);
    JSONObject markup = new JSONObject();
    markup.put("inline_keyboard", kb);
    return markup;
}

void editButton(long cid, long mid, String btnText, String cbData) {
    if (cid <= 0L || mid <= 0L || btnText == null || btnText.length() == 0) return;
    try {
        JSONObject payload = new JSONObject();
        payload.put("chat_id", cid);
        payload.put("message_id", mid);
        payload.put("reply_markup", makeInlineButtonMarkup(btnText, cbData));
        tgPost("editMessageReplyMarkup", payload, 5000);
    } catch (Exception e) {
    }
}

void notifyTargetFailure(long cid, long mid, boolean isMedia, String textMsg, String retryBtnText, boolean sendIfMissing) {
    if (cid <= 0L) return;
    if (isMedia && mid > 0L) {
        editButton(cid, mid, retryBtnText, "/qr");
    } else if (mid > 0L) {
        updateStatus(cid, mid, textMsg);
    } else if (sendIfMissing) {
        sendMsg(cid, textMsg, null);
    }
}

void notifyPreemptNotices(JSONArray notices) {
    if (notices == null) return;
    String cancelMsg = "❌ Request cancelled by VM reset. Please try again.";
    for (int i = 0; i < notices.length(); i++) {
        JSONObject nItem = notices.optJSONObject(i);
        if (nItem == null) continue;
        long nCid = nItem.optLong("chat_id", 0L);
        long nMid = nItem.optLong("status_message_id", 0L);
        boolean nMedia = nItem.optBoolean("status_is_media", false);
        notifyTargetFailure(nCid, nMid, nMedia, cancelMsg, "❌ Cancelled • 🔄 Retry", true);
    }
}"""

_BSH_AUDIT_HELPERS = """String eventLogPath = "/storage/emulated/0/Download/komobot_events.log";
String eventPrevLogPath = "/storage/emulated/0/Download/komobot_events.prev.log";

String cleanLogText(String s) {
    if (s == null) return "";
    return s.replace("\\r", " ").replace("\\n", " ").replace("|", "/").trim();
}

String todayStr(long ms) {
    return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date(ms));
}

String tsStr(long ms) {
    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date(ms));
}

String shortTs(long ms) {
    if (ms <= 0L) return "Never";
    return new SimpleDateFormat("MM-dd HH:mm", Locale.US).format(new Date(ms));
}

String formatSec(long ms) {
    if (ms <= 0L) return "0.0s";
    long tenths = (ms + 50L) / 100L;
    return (tenths / 10L) + "." + (tenths % 10L) + "s";
}

String formatUserDisplay(JSONObject cfg, long uid) {
    if (cfg == null) return "[" + uid + "]";
    JSONObject metaAll = cfg.optJSONObject("user_meta");
    JSONObject m = (metaAll != null) ? metaAll.optJSONObject(uid + "") : null;
    if (m == null) return "[" + uid + "]";
    String label = m.optString("label", "");
    String name = m.optString("name", "");
    String uname = m.optString("username", "");
    String base = (label.length() > 0) ? label : name;
    if (base.length() > 0 && uname.length() > 0) {
        return base + " (@" + uname + ") [" + uid + "]";
    }
    if (base.length() > 0) {
        return base + " [" + uid + "]";
    }
    if (uname.length() > 0) {
        return "@" + uname + " [" + uid + "]";
    }
    return "[" + uid + "]";
}

void ensureDayRollover(JSONObject st, String day) {
    if (!st.optString("day", "").equals(day)) {
        st.put("day", day);
        st.put("day_req", 0L);
        st.put("day_ok", 0L);
        st.put("day_fail", 0L);
    }
}

void writeConfigRaw(JSONObject cfg) {
    try {
        File outFile = new File(configPath);
        if (outFile.getParentFile() != null && !outFile.getParentFile().exists()) {
            outFile.getParentFile().mkdirs();
        }
        FileOutputStream fos = new FileOutputStream(outFile);
        OutputStreamWriter osw = new OutputStreamWriter(fos, "UTF-8");
        osw.write(cfg.toString(2));
        osw.flush();
        osw.close();
    } catch (Exception e) {
    }
}

void applyUsageToConfig(JSONObject cfg, long uid, String category, long elapsedMs, String outcome, String errDetail, long nowMs) {
    String day = todayStr(nowMs);
    JSONObject g = cfg.optJSONObject("global_stats");
    if (g == null) {
        g = new JSONObject();
        cfg.put("global_stats", g);
    }
    ensureDayRollover(g, day);

    if (category.equals("unauth")) {
        g.put("unauth", g.optLong("unauth", 0L) + 1L);
        return;
    }

    JSONObject allUsers = cfg.optJSONObject("user_stats");
    if (allUsers == null) {
        allUsers = new JSONObject();
        cfg.put("user_stats", allUsers);
    }
    String uidKey = uid + "";
    JSONObject u = (uid != 0L) ? allUsers.optJSONObject(uidKey) : null;
    if (uid != 0L && u == null) {
        u = new JSONObject();
        allUsers.put(uidKey, u);
    }
    if (u != null) {
        ensureDayRollover(u, day);
        u.put("last_ms", nowMs);
        u.put("last_outcome", outcome);
    }

    if (category.equals("locked")) {
        g.put("locked", g.optLong("locked", 0L) + 1L);
        if (u != null) {
            u.put("rejected", u.optLong("rejected", 0L) + 1L);
            u.put("last_error", cleanLogText(errDetail));
        }
    } else if (category.equals("ok")) {
        g.put("req", g.optLong("req", 0L) + 1L);
        g.put("ok", g.optLong("ok", 0L) + 1L);
        g.put("day_req", g.optLong("day_req", 0L) + 1L);
        g.put("day_ok", g.optLong("day_ok", 0L) + 1L);
        if (elapsedMs > 0L) g.put("total_ok_ms", g.optLong("total_ok_ms", 0L) + elapsedMs);
        if (u != null) {
            u.put("req", u.optLong("req", 0L) + 1L);
            u.put("ok", u.optLong("ok", 0L) + 1L);
            u.put("day_req", u.optLong("day_req", 0L) + 1L);
            u.put("day_ok", u.optLong("day_ok", 0L) + 1L);
            if (elapsedMs > 0L) u.put("total_ok_ms", u.optLong("total_ok_ms", 0L) + elapsedMs);
            u.put("last_error", "");
        }
    } else if (category.equals("fail")) {
        g.put("req", g.optLong("req", 0L) + 1L);
        g.put("fail", g.optLong("fail", 0L) + 1L);
        g.put("day_req", g.optLong("day_req", 0L) + 1L);
        g.put("day_fail", g.optLong("day_fail", 0L) + 1L);
        if (u != null) {
            u.put("req", u.optLong("req", 0L) + 1L);
            u.put("fail", u.optLong("fail", 0L) + 1L);
            u.put("day_req", u.optLong("day_req", 0L) + 1L);
            u.put("day_fail", u.optLong("day_fail", 0L) + 1L);
            u.put("last_error", cleanLogText(errDetail));
        }
    } else if (category.equals("cancel")) {
        g.put("req", g.optLong("req", 0L) + 1L);
        g.put("cancel", g.optLong("cancel", 0L) + 1L);
        g.put("day_req", g.optLong("day_req", 0L) + 1L);
        if (u != null) {
            u.put("req", u.optLong("req", 0L) + 1L);
            u.put("cancel", u.optLong("cancel", 0L) + 1L);
            u.put("day_req", u.optLong("day_req", 0L) + 1L);
            u.put("last_error", cleanLogText(errDetail));
        }
    }
}

void recordUsageSafe(long uid, String category, long elapsedMs, String outcome, String errDetail) {
    synchronized (System.class) {
        JSONObject fresh = new JSONObject();
        File f = new File(configPath);
        if (f.exists()) {
            try {
                FileInputStream fis = new FileInputStream(f);
                String raw = readStream(fis);
                fis.close();
                if (raw.length() > 0) fresh = new JSONObject(raw);
            } catch (Exception e) {
            }
        }
        applyUsageToConfig(fresh, uid, category, elapsedMs, outcome, errDetail, System.currentTimeMillis());
        writeConfigRaw(fresh);
    }
}

void appendAuditLog(String level, String event, long uid, String userDisp, String detail) {
    synchronized (System.class) {
        try {
            File f = new File(eventLogPath);
            if (f.getParentFile() != null && !f.getParentFile().exists()) {
                f.getParentFile().mkdirs();
            }
            if (f.exists() && f.length() >= 524288L) {
                File prev = new File(eventPrevLogPath);
                if (prev.exists()) {
                    prev.delete();
                }
                f.renameTo(prev);
            }
            String uCol = (userDisp != null && userDisp.length() > 0) ? cleanLogText(userDisp) : ("[" + uid + "]");
            String line = tsStr(System.currentTimeMillis()) + " | " + level + " | " + event + " | " + uCol + " | " + cleanLogText(detail) + "\\n";
            FileOutputStream fos = new FileOutputStream(f, true);
            fos.write(line.getBytes("UTF-8"));
            fos.close();
        } catch (Exception e) {
        }
    }
}

String buildFailureAlert(JSONObject cfg, String title, long targetCid, String triggerDesc, String reason, long elapsedMs, int stepCount, String lastState, String trace, int otherCnt, int whiteCnt, int loadCnt, String queuedSummary) {
    StringBuilder sb = new StringBuilder();
    sb.append(title).append("\\n");
    sb.append("• User: ").append(formatUserDisplay(cfg, targetCid)).append("\\n");
    if (triggerDesc != null && triggerDesc.length() > 0) {
        sb.append("• Trigger: ").append(triggerDesc).append("\\n");
    }
    sb.append("• Reason: ").append(reason).append("\\n");
    sb.append("• Last State: ").append(lastState).append(" (step ").append(stepCount).append(" • ").append(formatSec(elapsedMs)).append(")\\n");
    sb.append("• Counters: other=").append(otherCnt).append(", white=").append(whiteCnt).append(", loading=").append(loadCnt);
    if (trace != null && trace.length() > 0) {
        sb.append("\\n• Trace: ").append(trace);
    }
    if (queuedSummary != null && queuedSummary.length() > 0) {
        sb.append("\\n• Queued user request(s) failed: ").append(queuedSummary);
    }
    return sb.toString();
}

String recordPreemptedList(JSONObject cfg, JSONArray notices) {
    if (notices == null || notices.length() == 0) return "";
    long now = System.currentTimeMillis();
    StringBuilder summary = new StringBuilder();
    for (int i = 0; i < notices.length(); i++) {
        JSONObject nItem = notices.optJSONObject(i);
        if (nItem == null) continue;
        long nCid = nItem.optLong("chat_id", 0L);
        String role = nItem.optString("role", "active");
        String st = nItem.optString("last_state", "");
        long startMs = nItem.optLong("start_ms", 0L);
        long el = (startMs > 0L && now >= startMs) ? (now - startMs) : 0L;
        String uDisp = formatUserDisplay(cfg, nCid);
        recordUsageSafe(nCid, "cancel", el, "CANCELLED_RESET", role + (st.length() > 0 ? (" @ " + st) : ""));
        appendAuditLog("WARN", "CANCELLED_RESET", nCid, uDisp, role + (st.length() > 0 ? (" state=" + st) : "") + " elapsed=" + formatSec(el));
        if (summary.length() > 0) summary.append(", ");
        summary.append(uDisp).append(" (").append(role).append(")");
    }
    return summary.toString();
}"""

_BSH_TIMING_HELPER = """void logTiming(String tag, long a, long b) {
    try {
        File f = new File("/storage/emulated/0/Download/komobot_timing.log");
        if (f.exists() && f.length() > 12000L) {
            f.delete();
        }
        String line = System.currentTimeMillis() + "\\t" + tag + "\\t" + a + "\\t" + b + ";";
        FileOutputStream fos = new FileOutputStream(f, true);
        fos.write(line.getBytes("UTF-8"));
        fos.close();
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
            if (fresh.has("user_meta")) {
                cfg.put("user_meta", fresh.getJSONObject("user_meta"));
            }
            if (fresh.has("user_stats")) {
                cfg.put("user_stats", fresh.getJSONObject("user_stats"));
            }
            if (fresh.has("global_stats")) {
                cfg.put("global_stats", fresh.getJSONObject("global_stats"));
            }
            if (fresh.has("admin_pending_action")) {
                cfg.put("admin_pending_action", fresh.optString("admin_pending_action", ""));
                cfg.put("admin_pending_msg_id", fresh.optLong("admin_pending_msg_id", 0L));
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
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
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
String callbackId = "{{lv=callback_id}}".trim();
String callbackData = "{{lv=callback_data}}".trim();
String callbackMsgIdStr = "{{lv=callback_msg_id}}".trim();
String senderName = "{{lv=sender_name}}".trim();
String senderUsername = "{{lv=sender_username}}".trim();
String fwdUserIdStr = "{{lv=forward_user_id}}".trim();
if (callbackId.length() > 0 && callbackData.length() > 0) {{
    msgText = callbackData;
}}
long cbMsgId = 0L;
if (callbackId.length() > 0) {{
    try {{
        cbMsgId = Long.parseLong(callbackMsgIdStr);
    }} catch (Exception e) {{
    }}
}}
long fwdUserId = 0L;
try {{
    fwdUserId = Long.parseLong(fwdUserIdStr);
}} catch (Exception e) {{
}}

{_BSH_READ_STREAM}

{_BSH_PROGRESS_HELPER}

{_BSH_FRAME_HELPER}

{_BSH_TG_HTTP_HELPERS}

{_BSH_AUDIT_HELPERS}

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
    writeConfigRaw(cfg);
}}

void upsertUserMeta(JSONObject cfg, long uid, String fname, String uname, String customLabel, long nowMs, boolean setAdded) {{
    if (uid == 0L) return;
    JSONObject metaAll = cfg.optJSONObject("user_meta");
    if (metaAll == null) {{
        metaAll = new JSONObject();
        cfg.put("user_meta", metaAll);
    }}
    String key = uid + "";
    JSONObject m = metaAll.optJSONObject(key);
    if (m == null) {{
        m = new JSONObject();
        metaAll.put(key, m);
    }}
    String cleanName = cleanLogText(fname);
    if (cleanName.length() > 64) cleanName = cleanName.substring(0, 64);
    String cleanUname = cleanLogText(uname);
    if (cleanUname.length() > 64) cleanUname = cleanUname.substring(0, 64);
    String cleanLbl = cleanLogText(customLabel);
    if (cleanLbl.length() > 48) cleanLbl = cleanLbl.substring(0, 48);
    if (cleanName.length() > 0) m.put("name", cleanName);
    if (cleanUname.length() > 0) m.put("username", cleanUname);
    if (cleanLbl.length() > 0) m.put("label", cleanLbl);
    if (nowMs > 0L) m.put("last_seen_ms", nowMs);
    if (setAdded && m.optLong("added_ms", 0L) == 0L) m.put("added_ms", nowMs);
}}

boolean isAllowedInArray(JSONArray allowed, long targetId) {{
    if (allowed == null) return false;
    for (int i = 0; i < allowed.length(); i++) {{
        if (allowed.optLong(i, 0L) == targetId) return true;
    }}
    return false;
}}

boolean addAllowedUser(JSONObject cfg, long newId, String label, long nowMs) {{
    JSONArray allowed = cfg.optJSONArray("allowed_users");
    if (allowed == null) {{
        allowed = new JSONArray();
        cfg.put("allowed_users", allowed);
    }}
    boolean added = false;
    if (!isAllowedInArray(allowed, newId)) {{
        allowed.put(newId);
        cfg.put("allowed_users", allowed);
        added = true;
    }}
    upsertUserMeta(cfg, newId, "", "", label, 0L, true);
    if (added && cfg.optJSONObject("user_meta") != null) {{
        JSONObject m = cfg.optJSONObject("user_meta").optJSONObject(newId + "");
        if (m != null && m.optLong("added_ms", 0L) == 0L) m.put("added_ms", nowMs);
    }}
    return added;
}}

boolean removeAllowedUser(JSONObject cfg, long remId) {{
    JSONArray allowed = cfg.optJSONArray("allowed_users");
    if (allowed == null) return false;
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
    return found;
}}

JSONObject wrapInlineKb(JSONArray rows) {{
    JSONObject m = new JSONObject();
    m.put("inline_keyboard", rows);
    return m;
}}

JSONArray readAuditLines(boolean errorsOnly) {{
    JSONArray all = new JSONArray();
    String[] paths = new String[]{{eventPrevLogPath, eventLogPath}};
    for (int pi = 0; pi < paths.length; pi++) {{
        try {{
            File f = new File(paths[pi]);
            if (!f.exists()) continue;
            BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(f), "UTF-8"));
            String line;
            while ((line = br.readLine()) != null) {{
                if (line.length() == 0) continue;
                if (errorsOnly && line.indexOf(" | FAIL | ") < 0 && line.indexOf(" | ERR | ") < 0 && line.indexOf(" | WARN | ") < 0) {{
                    continue;
                }}
                all.put(line);
            }}
            br.close();
        }} catch (Exception e) {{
        }}
    }}
    if (all.length() <= 200) return all;
    JSONArray trimmed = new JSONArray();
    for (int i = all.length() - 200; i < all.length(); i++) {{
        trimmed.put(all.optString(i, ""));
    }}
    return trimmed;
}}

byte[] readAuditDocumentBytes() {{
    StringBuilder sb = new StringBuilder();
    String[] paths = new String[]{{eventPrevLogPath, eventLogPath}};
    for (int pi = 0; pi < paths.length; pi++) {{
        try {{
            File f = new File(paths[pi]);
            if (!f.exists()) continue;
            BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(f), "UTF-8"));
            String line;
            while ((line = br.readLine()) != null) {{
                if (line.length() > 0) sb.append(line).append("\\n");
            }}
            br.close();
        }} catch (Exception e) {{
        }}
    }}
    try {{
        return sb.toString().getBytes("UTF-8");
    }} catch (Exception e) {{
        return new byte[]{{}};
    }}
}}

JSONArray collectDisplayUserIds(JSONObject cfg, long adminId, boolean removableOnly) {{
    JSONArray ids = new JSONArray();
    if (!removableOnly && adminId > 0L) {{
        ids.put(adminId);
    }}
    JSONArray allowed = cfg.optJSONArray("allowed_users");
    if (allowed != null) {{
        for (int i = 0; i < allowed.length(); i++) {{
            long u = allowed.optLong(i, 0L);
            if (u == 0L || u == adminId) continue;
            if (!isAllowedInArray(ids, u)) ids.put(u);
        }}
    }}
    if (!removableOnly) {{
        JSONObject stats = cfg.optJSONObject("user_stats");
        if (stats != null) {{
            JSONArray keys = stats.names();
            if (keys != null) {{
                for (int i = 0; i < keys.length(); i++) {{
                    try {{
                        long u = Long.parseLong(keys.optString(i, "0"));
                        if (u != 0L && !isAllowedInArray(ids, u)) ids.put(u);
                    }} catch (Exception e) {{
                    }}
                }}
            }}
        }}
    }}
    return ids;
}}

JSONObject renderDashboard(JSONObject cfg, String tab, int page, long targetUid, long adminId) {{
    JSONObject out = new JSONObject();
    long now = System.currentTimeMillis();
    String day = todayStr(now);
    JSONObject g = cfg.optJSONObject("global_stats");
    if (g == null) g = new JSONObject();
    boolean sameDay = g.optString("day", "").equals(day);
    long dReq = sameDay ? g.optLong("day_req", 0L) : 0L;
    long dOk = sameDay ? g.optLong("day_ok", 0L) : 0L;
    long dFail = sameDay ? g.optLong("day_fail", 0L) : 0L;
    long tReq = g.optLong("req", 0L);
    long tOk = g.optLong("ok", 0L);
    long tFail = g.optLong("fail", 0L);
    long tCancel = g.optLong("cancel", 0L);
    long tUnauth = g.optLong("unauth", 0L);
    long tLocked = g.optLong("locked", 0L);
    long totalOkMs = g.optLong("total_ok_ms", 0L);
    long avgMs = (tOk > 0L) ? (totalOkMs / tOk) : 0L;
    JSONArray allowed = cfg.optJSONArray("allowed_users");
    int userCnt = (allowed != null) ? allowed.length() : 0;
    boolean pubAccess = cfg.optBoolean("public_access", true);

    if (tab.equals("add")) {{
        String txt = "➕ Add Authorized User\\n\\nSend a Telegram User ID (optionally followed by a label, e.g. `123456789 Alice`), or forward any message from that user.\\n\\nTap Cancel below or send /cancel to abort.";
        JSONArray rows = new JSONArray();
        JSONArray r1 = new JSONArray();
        r1.put(makeBtn("❌ Cancel", "adm:cancel"));
        rows.put(r1);
        out.put("text", txt);
        out.put("markup", wrapInlineKb(rows));
        return out;
    }}

    if (tab.equals("clrstats")) {{
        String txt = "🗑️ Reset Usage Counters?\\n\\nThis resets Today & Lifetime counters in komobot_config.json to 0.\\nAllowed users, user labels, and komobot_events.log are preserved.";
        JSONArray rows = new JSONArray();
        JSONArray r1 = new JSONArray();
        r1.put(makeBtn("✅ Confirm Reset Stats", "adm:clrstats_ok"));
        r1.put(makeBtn("❌ Cancel", "adm:home"));
        rows.put(r1);
        out.put("text", txt);
        out.put("markup", wrapInlineKb(rows));
        return out;
    }}

    if (tab.equals("rm")) {{
        String disp = formatUserDisplay(cfg, targetUid);
        String txt = "🗑️ Remove User?\\n\\nRemove " + disp + " from allowed users?\\nTheir historical log entries remain intact.";
        JSONArray rows = new JSONArray();
        JSONArray r1 = new JSONArray();
        r1.put(makeBtn("✅ Confirm Remove", "adm:rmok:" + targetUid));
        r1.put(makeBtn("❌ Cancel", "adm:rmenu:0"));
        rows.put(r1);
        out.put("text", txt);
        out.put("markup", wrapInlineKb(rows));
        return out;
    }}

    if (tab.equals("users") || tab.equals("rmenu")) {{
        boolean isRm = tab.equals("rmenu");
        JSONArray ids = collectDisplayUserIds(cfg, adminId, isRm);
        int pageSize = 5;
        int total = ids.length();
        int totalPages = (total == 0) ? 1 : ((total + pageSize - 1) / pageSize);
        if (page < 0) page = 0;
        if (page >= totalPages) page = totalPages - 1;
        int start = page * pageSize;
        int end = start + pageSize;
        if (end > total) end = total;

        JSONObject allStats = cfg.optJSONObject("user_stats");
        StringBuilder sb = new StringBuilder();
        if (isRm) {{
            sb.append("➖ Remove Authorized User (Page ").append(page + 1).append("/").append(totalPages).append(")\\n");
            if (total == 0) {{
                sb.append("\\nNo removable non-admin users registered.");
            }} else {{
                sb.append("\\nSelect a user below to remove:");
            }}
        }} else {{
            sb.append("👥 Users & Usage (Page ").append(page + 1).append("/").append(totalPages).append(" • ").append(userCnt).append(" allowed)\\n\\n");
            if (total == 0) {{
                sb.append("No users recorded yet.");
            }} else {{
                for (int i = start; i < end; i++) {{
                    long uId = ids.optLong(i, 0L);
                    boolean isAdm = (uId == adminId);
                    boolean inAllowed = isAdm || isAllowedInArray(allowed, uId);
                    String disp = formatUserDisplay(cfg, uId);
                    JSONObject u = (allStats != null) ? allStats.optJSONObject(uId + "") : null;
                    if (u == null) u = new JSONObject();
                    boolean uSame = u.optString("day", "").equals(day);
                    long uDReq = uSame ? u.optLong("day_req", 0L) : 0L;
                    long uReq = u.optLong("req", 0L);
                    long uOk = u.optLong("ok", 0L);
                    long uFail = u.optLong("fail", 0L);
                    long uCan = u.optLong("cancel", 0L);
                    long uRej = u.optLong("rejected", 0L);
                    long uAvg = (uOk > 0L) ? (u.optLong("total_ok_ms", 0L) / uOk) : 0L;
                    long uLast = u.optLong("last_ms", 0L);
                    String uOut = u.optString("last_outcome", "-");

                    sb.append(i + 1).append(". ");
                    if (isAdm) sb.append("👑 ");
                    sb.append(disp);
                    if (!inAllowed) sb.append(" [removed]");
                    sb.append("\\n");
                    sb.append("   Req: ").append(uReq).append(" (today ").append(uDReq).append(") | ✅ ").append(uOk);
                    if (uFail > 0L) sb.append(" ❌ ").append(uFail);
                    if (uCan > 0L) sb.append(" 🚫 ").append(uCan);
                    if (uRej > 0L) sb.append(" 🔒 ").append(uRej);
                    if (uOk > 0L) sb.append(" | avg ").append(formatSec(uAvg));
                    sb.append("\\n   Last: ").append(shortTs(uLast)).append(" • ").append(uOut).append("\\n");
                }}
            }}
        }}

        JSONArray rows = new JSONArray();
        if (isRm) {{
            for (int i = start; i < end; i++) {{
                long uId = ids.optLong(i, 0L);
                JSONArray rBtn = new JSONArray();
                rBtn.put(makeBtn("🗑️ " + formatUserDisplay(cfg, uId), "adm:rm:" + uId));
                rows.put(rBtn);
            }}
        }}
        String prefix = isRm ? "adm:rmenu:" : "adm:users:";
        JSONArray nav = new JSONArray();
        if (page > 0) nav.put(makeBtn("⬅️ Prev", prefix + (page - 1)));
        nav.put(makeBtn("🔄 Refresh", prefix + page));
        if (page + 1 < totalPages) nav.put(makeBtn("Next ➡️", prefix + (page + 1)));
        rows.put(nav);
        JSONArray act = new JSONArray();
        if (isRm) {{
            act.put(makeBtn("👥 Back to Users", "adm:users:0"));
        }} else {{
            act.put(makeBtn("➕ Add User", "adm:add"));
            act.put(makeBtn("➖ Remove", "adm:rmenu:0"));
        }}
        act.put(makeBtn("◀️ Dashboard", "adm:home"));
        rows.put(act);
        out.put("text", sb.toString());
        out.put("markup", wrapInlineKb(rows));
        return out;
    }}

    if (tab.equals("logs") || tab.equals("errs")) {{
        boolean errOnly = tab.equals("errs");
        JSONArray lines = readAuditLines(errOnly);
        int pageSize = 8;
        int total = lines.length();
        int totalPages = (total == 0) ? 1 : ((total + pageSize - 1) / pageSize);
        if (page < 0) page = 0;
        if (page >= totalPages) page = totalPages - 1;
        int endIdx = total - (page * pageSize);
        int startIdx = endIdx - pageSize;
        if (startIdx < 0) startIdx = 0;

        StringBuilder sb = new StringBuilder();
        sb.append(errOnly ? "🚨 Error & Alert Logs" : "📄 Recent Audit Logs");
        sb.append(" (Page ").append(page + 1).append("/").append(totalPages).append(" • ").append(total).append(" events)\\n\\n");
        if (total == 0) {{
            sb.append("No matching entries recorded on device yet.");
        }} else {{
            int cnt = endIdx - startIdx;
            for (int k = 0; k < cnt; k++) {{
                String ln = lines.optString(endIdx - 1 - k, "");
                if (ln.length() > 160) ln = ln.substring(0, 157) + "...";
                sb.append("• ").append(ln).append("\\n");
            }}
        }}
        String prefix = errOnly ? "adm:errs:" : "adm:logs:";
        JSONArray rows = new JSONArray();
        JSONArray r1 = new JSONArray();
        r1.put(makeBtn(errOnly ? "📄 Show All" : "🚨 Failures/Alerts", (errOnly ? "adm:logs:" : "adm:errs:") + "0"));
        r1.put(makeBtn("📎 Export File", "adm:export"));
        rows.put(r1);
        JSONArray r2 = new JSONArray();
        if (page > 0) r2.put(makeBtn("⬅️ Newer", prefix + (page - 1)));
        r2.put(makeBtn("🔄 Refresh", prefix + page));
        if (page + 1 < totalPages) r2.put(makeBtn("Older ➡️", prefix + (page + 1)));
        rows.put(r2);
        JSONArray r3 = new JSONArray();
        r3.put(makeBtn("◀️ Back to Dashboard", "adm:home"));
        rows.put(r3);
        out.put("text", sb.toString());
        out.put("markup", wrapInlineKb(rows));
        return out;
    }}

    // Default: Overview tab (adm:home)
    long busyUntil = cfg.optLong("busy_until", 0L);
    JSONArray q = cfg.optJSONArray("queue");
    int qLen = (q != null) ? q.length() : 0;
    String runStatus = "🟢 Idle (last: " + cfg.optString("last_state", "NONE") + ")";
    if (now < busyUntil && busyUntil > 0L) {{
        long actCid = cfg.optLong("active_chat_id", 0L);
        runStatus = "🟡 Active (" + cfg.optString("capture_mode", "qr") + " • " + formatUserDisplay(cfg, actCid) + " @ " + cfg.optString("last_state", "INIT") + ", Q=" + qLen + ")";
    }}
    long okPct = (tReq > 0L) ? ((tOk * 100L) / tReq) : 0L;
    StringBuilder sb = new StringBuilder();
    sb.append("👑 Komobot Admin Dashboard\\n\\n");
    sb.append("• Access: ").append(pubAccess ? "🟢 ENABLED (Public)" : "🔴 LOCKED (Admin only)").append("\\n");
    sb.append("• Status: ").append(runStatus).append("\\n");
    sb.append("• Users: ").append(userCnt).append(" authorized\\n\\n");
    sb.append("📊 Today (").append(day).append("): ")
      .append(dReq).append(" req | ✅ ").append(dOk).append(" | ❌ ").append(dFail).append("\\n");
    sb.append("📈 All-Time: ").append(tReq).append(" req | ✅ ").append(tOk)
      .append(" (").append(okPct).append("%) | ❌ ").append(tFail).append(" | 🚫 ").append(tCancel).append("\\n");
    sb.append("⏱️ Avg QR: ").append(formatSec(avgMs))
      .append(" | ⚠️ Blocked: ").append(tUnauth).append(" unauth, ").append(tLocked).append(" locked");

    JSONArray rows = new JSONArray();
    JSONArray r1 = new JSONArray();
    r1.put(makeBtn("👥 Users & Usage", "adm:users:0"));
    r1.put(makeBtn("📄 Recent Logs", "adm:logs:0"));
    rows.put(r1);
    JSONArray r2 = new JSONArray();
    r2.put(makeBtn(pubAccess ? "🔴 Lock Bot" : "🟢 Enable Public", "adm:toggle"));
    r2.put(makeBtn("🔄 Refresh", "adm:home"));
    rows.put(r2);
    JSONArray r3 = new JSONArray();
    r3.put(makeBtn("➕ Add User", "adm:add"));
    r3.put(makeBtn("➖ Remove User", "adm:rmenu:0"));
    rows.put(r3);
    JSONArray r4 = new JSONArray();
    r4.put(makeBtn("📎 Export Log File", "adm:export"));
    r4.put(makeBtn("🗑️ Reset Stats", "adm:clrstats"));
    rows.put(r4);
    out.put("text", sb.toString());
    out.put("markup", wrapInlineKb(rows));
    return out;
}}

long cid = 0L;
try {{
    cid = Long.parseLong(chatIdStr);
}} catch (Exception e) {{
    if (callbackId.length() > 0) answerCallback(callbackId, "");
    return "IGNORE";
}}
if (cid == 0L) {{
    if (callbackId.length() > 0) answerCallback(callbackId, "");
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
String callbackToast = "";
int qPos = 0;
boolean dupUid = false;
boolean isAdminUser = false;
boolean isMediaStatus = false;
boolean editDashboardInPlace = false;
boolean exportAuditDoc = false;
long notifyAdminCid = 0L;
String adminAlertText = null;
JSONObject adminAlertMarkup = null;
String auditLevel = null;
String auditEvent = null;
String auditUserDisp = "";
String auditDetail = "";
String crashedAlertText = null;
String crashedLogDetail = "";
long crashedLogCid = 0L;
String crashedLogUserDisp = "";
JSONArray crashedRestoreTargets = null;
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
        long now = System.currentTimeMillis();
        if (uid > 0L) {{
            cfg.put("last_update_id", uid);
        }}
        cfg.put("last_chat_id", cid);
        cfg.put("last_msg_text", msgText);
        // Only capture sender_name/username directly when not forwarding someone else's message
        if (fwdUserId == 0L) {{
            upsertUserMeta(cfg, cid, senderName, senderUsername, "", now, false);
        }} else {{
            upsertUserMeta(cfg, cid, "", "", "", now, false);
        }}

        long adminId = cfg.optLong("admin_id", defaultAdminId);
        if (!cfg.has("admin_id") && adminId > 0L) {{
            cfg.put("admin_id", adminId);
        }}
        notifyAdminCid = adminId;
        JSONArray allowed = cfg.optJSONArray("allowed_users");
        if (allowed == null) {{
            allowed = new JSONArray();
            allowed.put(adminId);
            cfg.put("allowed_users", allowed);
        }}

        boolean isAdmin = (cid == adminId);
        isAdminUser = isAdmin;
        boolean isAllowed = isAdmin || isAllowedInArray(allowed, cid);

        // Close abandoned lease stats if previous run expired mid-flight without cleanup
        long busyUntil = cfg.optLong("busy_until", 0L);
        boolean willRecoverStale = false;
        JSONObject staleCrashPayload = null;
        if (busyUntil > 0L && now >= busyUntil) {{
            long staleCid = cfg.optLong("active_chat_id", 0L);
            String staleState = cfg.optString("last_state", "INIT");
            if (staleCid != 0L && !staleState.equals("QR_SENT") && !staleState.equals("RESET")) {{
                willRecoverStale = true;
                long staleStart = cfg.optLong("active_start_ms", cfg.optLong("run_start_ms", 0L));
                long staleElapsed = (staleStart > 0L && now >= staleStart) ? (now - staleStart) : 0L;
                int staleStep = cfg.optInt("step_count", 0);
                String staleTrace = cfg.optString("state_trace", "");
                String staleTrig = cfg.optString("active_trigger", "cmd");
                applyUsageToConfig(cfg, staleCid, "fail", staleElapsed, "LEASE_EXPIRED_CRASH", "state=" + staleState, now);

                JSONArray staleQ = cfg.optJSONArray("queue");
                JSONArray restoreList = new JSONArray();
                JSONObject actT = new JSONObject();
                actT.put("chat_id", staleCid);
                actT.put("status_message_id", cfg.optLong("status_message_id", 0L));
                actT.put("status_is_media", cfg.optBoolean("status_is_media", false));
                restoreList.put(actT);

                StringBuilder qNames = new StringBuilder();
                if (staleQ != null) {{
                    for (int qi = 0; qi < staleQ.length(); qi++) {{
                        JSONObject qIt = staleQ.optJSONObject(qi);
                        if (qIt == null) continue;
                        long qCid = qIt.optLong("chat_id", 0L);
                        long qEnq = qIt.optLong("enqueued_ms", staleStart);
                        applyUsageToConfig(cfg, qCid, "fail", (now >= qEnq) ? (now - qEnq) : 0L, "LEASE_EXPIRED_CRASH", "queued", now);
                        restoreList.put(qIt);
                        if (qNames.length() > 0) qNames.append(", ");
                        qNames.append(formatUserDisplay(cfg, qCid));
                    }}
                }}

                String alertTxt = buildFailureAlert(
                    cfg,
                    "🚨 Previous Request Interrupted (Lease Expired)",
                    staleCid,
                    staleTrig,
                    "Worker stopped before finishing (LEASE_EXPIRED_CRASH)",
                    staleElapsed,
                    staleStep,
                    staleState,
                    staleTrace,
                    cfg.optInt("other_count", 0),
                    cfg.optInt("white_count", 0),
                    cfg.optInt("loading_count", 0),
                    qNames.toString()
                );
                staleCrashPayload = new JSONObject();
                staleCrashPayload.put("alert", alertTxt);
                staleCrashPayload.put("cid", staleCid);
                staleCrashPayload.put("user_disp", formatUserDisplay(cfg, staleCid));
                staleCrashPayload.put("detail", "state=" + staleState + " step=" + staleStep + " elapsed=" + formatSec(staleElapsed) + " trace=" + staleTrace);
                staleCrashPayload.put("targets", restoreList);

                cfg.put("busy_until", 0L);
                cfg.put("queue", new JSONArray());
                cfg.put("worker_active", false);
                cfg.put("worker_pending_start_ms", 0L);
                cfg.put("worker_exiting_ms", 0L);
            }}
        }}

        String pendAction = isAdmin ? cfg.optString("admin_pending_action", "") : "";
        boolean clearsAddPrompt = msgText.equalsIgnoreCase("/qr")
            || msgText.indexOf("Take QR Screenshot") >= 0
            || msgText.indexOf("Reset VM") >= 0
            || msgText.equals("/start")
            || msgText.equals("/dashboard")
            || msgText.equals("/admin")
            || msgText.indexOf("Admin Dashboard") >= 0
            || msgText.equals("/listusers")
            || msgText.indexOf("List Users") >= 0
            || msgText.equals("/toggle")
            || msgText.indexOf("Toggle Public Access") >= 0
            || msgText.equals("/usage")
            || msgText.equals("/logs")
            || msgText.equals("/exportlogs")
            || (callbackId.length() > 0);
        if (isAdmin && pendAction.length() > 0 && clearsAddPrompt) {{
            cfg.put("admin_pending_action", "");
            pendAction = "";
        }}

        if (!isAllowed) {{
            applyUsageToConfig(cfg, cid, "unauth", 0L, "UNAUTHORIZED", msgText, now);
            String uDisp = formatUserDisplay(cfg, cid);
            saveConfig(cfg);
            replyText = "⛔ Unauthorized. Your ID: " + cid;
            auditLevel = "WARN";
            auditEvent = "UNAUTHORIZED";
            auditUserDisp = uDisp;
            auditDetail = "input=" + msgText;
            if (adminId > 0L) {{
                adminAlertText = "🚫 Unauthorized Access Attempt\\n• From: " + uDisp + "\\n• Input: " + cleanLogText(msgText) + "\\n• Time: " + tsStr(now);
                JSONArray r1 = new JSONArray();
                r1.put(makeBtn("➕ Authorize " + cid, "adm:addid:" + cid));
                JSONArray rows = new JSONArray();
                rows.put(r1);
                adminAlertMarkup = wrapInlineKb(rows);
            }}
        }} else if (callbackId.length() > 0 && callbackData.startsWith("adm:")) {{
            if (!isAdmin) {{
                applyUsageToConfig(cfg, cid, "unauth", 0L, "UNAUTHORIZED_ADMIN_CB", callbackData, now);
                String uDisp = formatUserDisplay(cfg, cid);
                saveConfig(cfg);
                callbackToast = "⛔ Admin only.";
                auditLevel = "WARN";
                auditEvent = "UNAUTHORIZED";
                auditUserDisp = uDisp;
                auditDetail = "admin_cb=" + callbackData;
                if (adminId > 0L) {{
                    adminAlertText = "🚫 Unauthorized Admin Callback\\n• From: " + uDisp + "\\n• Data: " + cleanLogText(callbackData);
                }}
            }} else {{
                String sub = callbackData.substring(4);
                String viewTab = "home";
                int viewPage = 0;
                long viewUid = 0L;
                boolean renderCard = true;
                if (sub.equals("home")) {{
                    viewTab = "home";
                }} else if (sub.equals("toggle")) {{
                    boolean pub = !cfg.optBoolean("public_access", true);
                    cfg.put("public_access", pub);
                    callbackToast = pub ? "🟢 Public access ENABLED" : "🔴 Bot LOCKED";
                    auditLevel = "ADMIN";
                    auditEvent = "PUBLIC_TOGGLE";
                    auditUserDisp = formatUserDisplay(cfg, cid);
                    auditDetail = "public_access=" + pub;
                    viewTab = "home";
                }} else if (sub.startsWith("users:")) {{
                    viewTab = "users";
                    try {{ viewPage = (int) Long.parseLong(sub.substring(6)); }} catch (Exception e) {{}}
                }} else if (sub.startsWith("logs:")) {{
                    viewTab = "logs";
                    try {{ viewPage = (int) Long.parseLong(sub.substring(5)); }} catch (Exception e) {{}}
                }} else if (sub.startsWith("errs:")) {{
                    viewTab = "errs";
                    try {{ viewPage = (int) Long.parseLong(sub.substring(5)); }} catch (Exception e) {{}}
                }} else if (sub.equals("add")) {{
                    cfg.put("admin_pending_action", "add_user");
                    cfg.put("admin_pending_msg_id", cbMsgId);
                    viewTab = "add";
                }} else if (sub.equals("cancel")) {{
                    cfg.put("admin_pending_action", "");
                    callbackToast = "Cancelled";
                    viewTab = "home";
                }} else if (sub.startsWith("rmenu:")) {{
                    viewTab = "rmenu";
                    try {{ viewPage = (int) Long.parseLong(sub.substring(6)); }} catch (Exception e) {{}}
                }} else if (sub.startsWith("rm:")) {{
                    viewTab = "rm";
                    try {{ viewUid = Long.parseLong(sub.substring(3)); }} catch (Exception e) {{}}
                }} else if (sub.startsWith("rmok:")) {{
                    long remId = 0L;
                    try {{ remId = Long.parseLong(sub.substring(5)); }} catch (Exception e) {{}}
                    if (remId != 0L && remId != adminId && removeAllowedUser(cfg, remId)) {{
                        callbackToast = "🗑️ Removed " + remId;
                        auditLevel = "ADMIN";
                        auditEvent = "USER_REMOVED";
                        auditUserDisp = formatUserDisplay(cfg, cid);
                        auditDetail = "removed=" + formatUserDisplay(cfg, remId);
                    }} else {{
                        callbackToast = "⚠️ Cannot remove " + remId;
                    }}
                    viewTab = "users";
                }} else if (sub.startsWith("addid:")) {{
                    long newId = 0L;
                    try {{ newId = Long.parseLong(sub.substring(6)); }} catch (Exception e) {{}}
                    if (newId != 0L) {{
                        addAllowedUser(cfg, newId, "", now);
                        callbackToast = "✅ Authorized " + newId;
                        auditLevel = "ADMIN";
                        auditEvent = "USER_ADDED";
                        auditUserDisp = formatUserDisplay(cfg, cid);
                        auditDetail = "added=" + formatUserDisplay(cfg, newId) + " via=alert_btn";
                        replyText = "✅ Authorized " + formatUserDisplay(cfg, newId);
                        JSONArray rows = new JSONArray();
                        JSONArray r1 = new JSONArray();
                        r1.put(makeBtn("📊 Open Dashboard", "adm:home"));
                        rows.put(r1);
                        replyMarkup = wrapInlineKb(rows);
                        editDashboardInPlace = (cbMsgId > 0L);
                    }}
                    renderCard = false;
                }} else if (sub.equals("clrstats")) {{
                    viewTab = "clrstats";
                }} else if (sub.equals("clrstats_ok")) {{
                    cfg.put("user_stats", new JSONObject());
                    cfg.put("global_stats", new JSONObject());
                    callbackToast = "🗑️ Usage stats cleared";
                    auditLevel = "ADMIN";
                    auditEvent = "STATS_CLEARED";
                    auditUserDisp = formatUserDisplay(cfg, cid);
                    auditDetail = "cleared=all_usage";
                    viewTab = "home";
                }} else if (sub.equals("export")) {{
                    exportAuditDoc = true;
                    callbackToast = "📎 Exporting log file...";
                    renderCard = false;
                }}
                if (renderCard) {{
                    JSONObject view = renderDashboard(cfg, viewTab, viewPage, viewUid, adminId);
                    replyText = view.optString("text", "");
                    replyMarkup = view.optJSONObject("markup");
                    editDashboardInPlace = (cbMsgId > 0L);
                }}
                saveConfig(cfg);
            }}
        }} else if (isAdmin && pendAction.equals("add_user")) {{
            if (msgText.equalsIgnoreCase("/cancel")) {{
                cfg.put("admin_pending_action", "");
                saveConfig(cfg);
                JSONObject view = renderDashboard(cfg, "home", 0, 0L, adminId);
                replyText = "❌ Add user cancelled.\\n\\n" + view.optString("text", "");
                replyMarkup = view.optJSONObject("markup");
            }} else {{
                long targetId = 0L;
                String lbl = "";
                if (fwdUserId != 0L) {{
                    targetId = fwdUserId;
                    lbl = cleanLogText(senderName);
                }} else {{
                    int spIdx = msgText.indexOf(" ");
                    String idPart = (spIdx >= 0) ? msgText.substring(0, spIdx).trim() : msgText.trim();
                    lbl = (spIdx >= 0) ? cleanLogText(msgText.substring(spIdx + 1)) : "";
                    try {{
                        targetId = Long.parseLong(idPart);
                    }} catch (Exception e) {{
                    }}
                }}
                if (targetId != 0L) {{
                    cfg.put("admin_pending_action", "");
                    boolean added = addAllowedUser(cfg, targetId, lbl, now);
                    saveConfig(cfg);
                    String disp = formatUserDisplay(cfg, targetId);
                    auditLevel = "ADMIN";
                    auditEvent = "USER_ADDED";
                    auditUserDisp = formatUserDisplay(cfg, cid);
                    auditDetail = "target=" + disp + (added ? " (new)" : " (updated)");
                    replyText = (added ? "✅ User authorized: " : "ℹ️ User already authorized (updated): ") + disp;
                    JSONArray rows = new JSONArray();
                    JSONArray r1 = new JSONArray();
                    r1.put(makeBtn("👥 Users & Usage", "adm:users:0"));
                    r1.put(makeBtn("📊 Dashboard", "adm:home"));
                    rows.put(r1);
                    replyMarkup = wrapInlineKb(rows);
                }} else {{
                    saveConfig(cfg);
                    replyText = "⚠️ Could not read a Telegram User ID (forwarded senders with privacy enabled hide IDs).\\nSend `<id> [label]` (e.g. `123456789 Alice`), or tap Cancel.";
                    JSONArray rows = new JSONArray();
                    JSONArray r1 = new JSONArray();
                    r1.put(makeBtn("❌ Cancel", "adm:cancel"));
                    rows.put(r1);
                    replyMarkup = wrapInlineKb(rows);
                }}
            }}
        }} else if (msgText.equals("/start")) {{
            JSONObject markup = new JSONObject();
            markup.put("resize_keyboard", true);
            JSONArray keyboard = new JSONArray();
            if (isAdmin) {{
                JSONArray r1 = new JSONArray();
                r1.put("📸 Take QR Screenshot");
                JSONArray r2 = new JSONArray();
                r2.put("📊 Admin Dashboard");
                r2.put("🧹 Reset VM App");
                JSONArray r3 = new JSONArray();
                r3.put("👥 List Users");
                r3.put("🛑 Toggle Public Access");
                keyboard.put(r1);
                keyboard.put(r2);
                keyboard.put(r3);
                markup.put("keyboard", keyboard);
                saveConfig(cfg);
                replyText = "👑 Admin Control Ready\\nTap 📊 Admin Dashboard or use /dashboard, /adduser <id> [name], /removeuser <id>, /listusers, /logs, /exportlogs, /toggle.";
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
        }} else if (isAdmin && (msgText.equals("/dashboard") || msgText.equals("/admin") || msgText.indexOf("Admin Dashboard") >= 0)) {{
            saveConfig(cfg);
            JSONObject view = renderDashboard(cfg, "home", 0, 0L, adminId);
            replyText = view.optString("text", "");
            replyMarkup = view.optJSONObject("markup");
        }} else if (isAdmin && (msgText.equals("/usage") || msgText.equals("/listusers") || msgText.indexOf("List Users") >= 0)) {{
            saveConfig(cfg);
            JSONObject view = renderDashboard(cfg, "users", 0, 0L, adminId);
            replyText = view.optString("text", "");
            replyMarkup = view.optJSONObject("markup");
        }} else if (isAdmin && msgText.equals("/logs")) {{
            saveConfig(cfg);
            JSONObject view = renderDashboard(cfg, "logs", 0, 0L, adminId);
            replyText = view.optString("text", "");
            replyMarkup = view.optJSONObject("markup");
        }} else if (isAdmin && msgText.equals("/exportlogs")) {{
            saveConfig(cfg);
            exportAuditDoc = true;
        }} else if (isAdmin && msgText.startsWith("/adduser")) {{
            String arg = msgText.substring(8).trim();
            try {{
                int spIdx = arg.indexOf(" ");
                String idPart = (spIdx >= 0) ? arg.substring(0, spIdx).trim() : arg;
                String lbl = (spIdx >= 0) ? cleanLogText(arg.substring(spIdx + 1)) : "";
                long newId = Long.parseLong(idPart);
                addAllowedUser(cfg, newId, lbl, now);
                saveConfig(cfg);
                String disp = formatUserDisplay(cfg, newId);
                replyText = "✅ User " + disp + " added.";
                auditLevel = "ADMIN";
                auditEvent = "USER_ADDED";
                auditUserDisp = formatUserDisplay(cfg, cid);
                auditDetail = "added=" + disp;
            }} catch (Exception e) {{
                saveConfig(cfg);
                replyText = "⚠️ Usage: /adduser <telegram_id> [optional name]";
            }}
        }} else if (isAdmin && msgText.startsWith("/removeuser")) {{
            String arg = msgText.substring(11).trim();
            try {{
                long remId = Long.parseLong(arg);
                if (remId == adminId) {{
                    saveConfig(cfg);
                    replyText = "⚠️ Cannot remove the admin ID.";
                }} else {{
                    boolean found = removeAllowedUser(cfg, remId);
                    String disp = formatUserDisplay(cfg, remId);
                    saveConfig(cfg);
                    if (found) {{
                        replyText = "🗑️ User " + disp + " removed.";
                        auditLevel = "ADMIN";
                        auditEvent = "USER_REMOVED";
                        auditUserDisp = formatUserDisplay(cfg, cid);
                        auditDetail = "removed=" + disp;
                    }} else {{
                        replyText = "🛑 User " + remId + " is not in the allowed list.";
                    }}
                }}
            }} catch (Exception e) {{
                saveConfig(cfg);
                replyText = "⚠️ Usage: /removeuser <telegram_id>";
            }}
        }} else if (isAdmin && (msgText.equals("/toggle") || msgText.indexOf("Toggle Public Access") >= 0)) {{
            boolean pub = !cfg.optBoolean("public_access", true);
            cfg.put("public_access", pub);
            String uDisp = formatUserDisplay(cfg, cid);
            saveConfig(cfg);
            replyText = "Public access is now " + (pub ? "🟢 ENABLED." : "🔴 DISABLED.");
            auditLevel = "ADMIN";
            auditEvent = "PUBLIC_TOGGLE";
            auditUserDisp = uDisp;
            auditDetail = "public_access=" + pub;
        }} else if (callbackId.length() > 0 && callbackData.equals("noop")) {{
            saveConfig(cfg);
            callbackToast = "⏳ Refresh already in progress...";
        }} else if (msgText.startsWith("/") && !msgText.equalsIgnoreCase("/qr")) {{
            saveConfig(cfg);
            replyText = "ℹ️ Commands: /start, /qr" + (isAdmin ? ", /dashboard, /usage, /adduser <id> [name], /removeuser <id>, /listusers, /logs, /exportlogs, /toggle" : "");
        }} else {{
            boolean pubAccess = cfg.optBoolean("public_access", true);
            if (!pubAccess && !isAdmin) {{
                applyUsageToConfig(cfg, cid, "locked", 0L, "LOCKED", msgText, now);
                String uDisp = formatUserDisplay(cfg, cid);
                saveConfig(cfg);
                replyText = "⚠️ The bot is currently locked by the admin.";
                auditLevel = "WARN";
                auditEvent = "BLOCKED_LOCKED";
                auditUserDisp = uDisp;
                auditDetail = "input=" + msgText;
                if (adminId > 0L) {{
                    adminAlertText = "🔒 Blocked Request (Bot Locked)\\n• User: " + uDisp + "\\n• Input: " + cleanLogText(msgText) + "\\n• Time: " + tsStr(now);
                }}
            }} else {{
                busyUntil = cfg.optLong("busy_until", 0L);
                String lowerMsg = msgText.toLowerCase();
                String requestedMode = "";
                if (isAdmin && msgText.indexOf("Reset VM") >= 0) {{
                    requestedMode = "reset";
                }} else if (lowerMsg.equals("/qr") || lowerMsg.equals("qr") || msgText.indexOf("Take QR Screenshot") >= 0 || lowerMsg.indexOf("qr") >= 0 || lowerMsg.indexOf("screenshot") >= 0) {{
                    requestedMode = "qr";
                }}
                boolean isMediaRefresh = callbackId.length() > 0 && cbMsgId > 0L && requestedMode.equals("qr");
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
                            String busyMsg = "⏳ Your request is already in progress.";
                            if (callbackId.length() > 0) {{
                                callbackToast = busyMsg;
                            }} else {{
                                replyText = busyMsg;
                            }}
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
                            String qBusy = "⏳ You are already in the queue (#" + (dupIdx + 1) + ").";
                            if (callbackId.length() > 0) {{
                                callbackToast = qBusy;
                            }} else {{
                                replyText = qBusy;
                            }}
                        }} else {{
                            qPos = queue.length() + 1;
                            JSONObject item = new JSONObject();
                            item.put("chat_id", cid);
                            item.put("status_message_id", isMediaRefresh ? cbMsgId : 0L);
                            item.put("status_is_media", isMediaRefresh);
                            item.put("trigger", isMediaRefresh ? "queued_media" : "queued_cmd");
                            item.put("enqueued_ms", now);
                            queue.put(item);
                            cfg.put("queue", queue);
                            cfg.put("busy_until", busyUntil + 30000L);
                            saveConfig(cfg);
                            statusStage = "QUEUE";
                            isMediaStatus = isMediaRefresh;
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
                                pActive.put("status_is_media", cfg.optBoolean("status_is_media", false));
                                pActive.put("role", "active");
                                pActive.put("last_state", cfg.optString("last_state", "INIT"));
                                pActive.put("start_ms", cfg.optLong("active_start_ms", cfg.optLong("run_start_ms", 0L)));
                                displaced.put(pActive);
                            }}
                            JSONArray prevQ = cfg.optJSONArray("queue");
                            if (prevQ != null) {{
                                for (int qi = 0; qi < prevQ.length(); qi++) {{
                                    JSONObject qItem = prevQ.optJSONObject(qi);
                                    if (qItem != null && qItem.optLong("chat_id", 0L) != 0L) {{
                                        JSONObject qCopy = new JSONObject(qItem.toString());
                                        qCopy.put("role", "queued #" + (qi + 1));
                                        qCopy.put("start_ms", qItem.optLong("enqueued_ms", now));
                                        displaced.put(qCopy);
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
                        cfg.put("active_trigger", requestedMode.equals("reset") ? "reset" : (isMediaRefresh ? "callback_media" : "cmd"));
                        cfg.put("active_start_ms", runStart);
                        cfg.put("state_trace", "INIT");
                        cfg.put("queue", new JSONArray());
                        cfg.put("qr_was_closed", false);
                        cfg.put("reset_notified", false);
                        cfg.put("reset_stage", 0);
                        cfg.put("reset_kills", 0);
                        cfg.put("reset_recents_checked", false);
                        cfg.put("reset_open_tries", 0);
                        cfg.put("step_count", 0);
                        cfg.put("row_tap_ms", 0L);
                        cfg.put("other_count", 0);
                        cfg.put("white_count", 0);
                        cfg.put("loading_count", 0);
                        cfg.put("last_state", "INIT");
                        cfg.put("progress_pct", (isAdmin && !isMediaRefresh) ? 0 : 10);
                        cfg.put("pending_status_text", "");
                        cfg.put("pending_delete_cid", 0L);
                        cfg.put("pending_delete_mid", 0L);
                        cfg.put("vm_seen", false);
                        cfg.put("vm_launched", false);
                        cfg.put("last_ss_deleted", true);
                        cfg.put("run_start_ms", runStart);
                        cfg.put("status_is_media", isMediaRefresh);
                        cfg.put("media_init_pending", isMediaRefresh);
                        cfg.put("status_message_id", isMediaRefresh ? cbMsgId : 0L);
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
                            auditLevel = "ADMIN";
                            auditEvent = "RESET_START";
                            auditUserDisp = formatUserDisplay(cfg, cid);
                            auditDetail = "mode=coop displaced=" + displaced.length();
                        }} else {{
                            if (willRecoverStale && staleCrashPayload != null) {{
                                cfg.put("crashed_notice", staleCrashPayload);
                                willRecoverStale = false;
                            }}
                            JSONArray preemptNotices = cfg.optJSONArray("preempted_notices");
                            if (preemptNotices == null) {{
                                preemptNotices = new JSONArray();
                            }}
                            for (int di = 0; di < displaced.length(); di++) {{
                                preemptNotices.put(displaced.get(di));
                            }}
                            cfg.put("preempted_notices", preemptNotices);
                            cfg.put("vm_booting", false);
                            cfg.put("pending_cb_id", callbackId);
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
        if (willRecoverStale && staleCrashPayload != null) {{
            crashedAlertText = staleCrashPayload.optString("alert", "");
            crashedLogCid = staleCrashPayload.optLong("cid", 0L);
            crashedLogUserDisp = staleCrashPayload.optString("user_disp", "");
            crashedLogDetail = staleCrashPayload.optString("detail", "");
            crashedRestoreTargets = staleCrashPayload.optJSONArray("targets");
        }}
    }}
}}

if (dupUid) {{
    return "IGNORE";
}}
if (actionResult.equals("RUN")) {{
    return "RUN";
}}
if (auditLevel != null) {{
    appendAuditLog(auditLevel, auditEvent, cid, auditUserDisp, auditDetail);
}}
if (crashedAlertText != null && crashedAlertText.length() > 0) {{
    appendAuditLog("FAIL", "QR_FAIL_CRASH_LEASE", crashedLogCid, crashedLogUserDisp, crashedLogDetail);
    if (crashedRestoreTargets != null) {{
        for (int ti = 0; ti < crashedRestoreTargets.length(); ti++) {{
            JSONObject t = crashedRestoreTargets.optJSONObject(ti);
            if (t == null) continue;
            notifyTargetFailure(t.optLong("chat_id", 0L), t.optLong("status_message_id", 0L), t.optBoolean("status_is_media", false), "❌ Previous request was interrupted. Please try again.", "⚠️ Interrupted • 🔄 Retry", false);
        }}
    }}
    if (notifyAdminCid > 0L) {{
        sendMsg(notifyAdminCid, crashedAlertText, null);
    }}
}}
if (callbackId.length() > 0) {{
    answerCallback(callbackId, callbackToast);
}}
if (statusStage.equals("COOP_RESET")) {{
    String coopPreemptSummary = "";
    if (coopPreemptNotices != null && coopPreemptNotices.length() > 0) {{
        JSONObject curCfg = loadConfig();
        coopPreemptSummary = recordPreemptedList(curCfg, coopPreemptNotices);
    }}
    String resetMsgText = "🔄 Force-restarting Telcell Wallet...";
    if (coopPreemptSummary.length() > 0) {{
        resetMsgText = resetMsgText + "\\n\\nℹ️ Cancelled " + coopPreemptNotices.length() + " pending: " + coopPreemptSummary;
    }}
    JSONObject sent = sendMsg(cid, resetMsgText, null);
    long resetMsgId = sent.has("result") ? sent.getJSONObject("result").optLong("message_id", 0L) : 0L;
    if (resetMsgId > 0L) {{
        synchronized (System.class) {{
            JSONObject fresh = loadConfig();
            if (fresh.optLong("active_chat_id", 0L) == cid
                && fresh.optLong("run_start_ms", 0L) == coopRunStart
                && fresh.optLong("status_message_id", 0L) == 0L) {{
                fresh.put("status_message_id", resetMsgId);
                fresh.put("status_is_media", false);
                fresh.put("media_init_pending", false);
                fresh.put("last_ss_deleted", true);
                saveConfig(fresh);
            }}
        }}
    }}
    notifyPreemptNotices(coopPreemptNotices);
    return "IGNORE";
}}
if (exportAuditDoc) {{
    byte[] docBytes = readAuditDocumentBytes();
    if (docBytes.length == 0) {{
        sendMsg(cid, "ℹ️ No audit log entries recorded on device yet.", null);
    }} else {{
        JSONObject extra = new JSONObject();
        extra.put("caption", "📄 Komobot Audit Log (" + docBytes.length + " bytes)");
        postMultipartRaw("sendDocument", cid, 0L, extra, "document", "komobot_events.log", "text/plain", docBytes, 15000);
    }}
}}
if (replyText != null) {{
    if (editDashboardInPlace && cbMsgId > 0L) {{
        editMsg(cid, cbMsgId, replyText, replyMarkup);
    }} else {{
        sendMsg(cid, replyText, replyMarkup);
    }}
}} else if (statusStage.equals("QUEUE")) {{
    if (isMediaStatus && cbMsgId > 0L) {{
        editButton(cid, cbMsgId, "⏳ Queued (#" + qPos + ")...", "noop");
    }} else {{
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
}}
if (adminAlertText != null && notifyAdminCid > 0L && cid != notifyAdminCid) {{
    sendMsg(notifyAdminCid, adminAlertText, adminAlertMarkup);
}}
return actionResult;
"""


def build_init_status_script() -> str:
    """BeanShell Java 7 script sending initial status while Virtual Master boots."""
    return (
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import java.text.SimpleDateFormat;\n"
        "import java.util.Date;\n"
        "import java.util.Locale;\n"
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
        + _BSH_AUDIT_HELPERS
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
String pendingCbId = "";
boolean statusIsMedia = false;
boolean mediaInitPending = false;
synchronized (System.class) {
    JSONObject cfg = loadConfig();
    cfg.put("worker_pending_start_ms", 0L);
    cfg.put("worker_heartbeat_ms", System.currentTimeMillis());
    pendingCbId = cfg.optString("pending_cb_id", "");
    if (pendingCbId.length() > 0) {
        cfg.put("pending_cb_id", "");
    }
    statusIsMedia = cfg.optBoolean("status_is_media", false);
    mediaInitPending = cfg.optBoolean("media_init_pending", false);
    if (mediaInitPending) {
        cfg.put("media_init_pending", false);
    }
    saveConfig(cfg);
    cid = cfg.optLong("active_chat_id", 0L);
    adminId = cfg.optLong("admin_id", 0L);
    claimedRunStart = cfg.optLong("run_start_ms", 0L);
    existingMid = cfg.optLong("status_message_id", 0L);
    captureMode = cfg.optString("capture_mode", "qr");
}
if (cid <= 0L || (existingMid > 0L && !mediaInitPending)) {
    if (pendingCbId.length() > 0) {
        answerCallback(pendingCbId, "");
    }
    return "SKIP";
}

long statusMsgId = 0L;
if (statusIsMedia && existingMid > 0L) {
    // Flip the button to the progress bar first; the callback spinner is cleared right after.
    editButton(cid, existingMid, formatButtonProgress(10), "noop");
    if (pendingCbId.length() > 0) {
        answerCallback(pendingCbId, "");
        pendingCbId = "";
    }
    statusMsgId = existingMid;
} else {
    if (pendingCbId.length() > 0) {
        answerCallback(pendingCbId, "");
        pendingCbId = "";
    }
    String initText = captureMode.equals("reset")
        ? "🔄 Force-restarting Telcell Wallet..."
        : ((cid == adminId)
            ? "🔍 Waking phone & checking Virtual Master..."
            : formatProgress("⏳ Generating QR code...", 10));
    JSONObject sent = sendMsg(cid, initText, null);
    statusMsgId = sent.has("result") ? sent.getJSONObject("result").optLong("message_id", 0L) : 0L;
}
JSONArray preemptNotices = null;
JSONObject crashedNotice = null;
JSONObject latestSnapshot = null;
boolean deleteOrphanedMsg = false;
synchronized (System.class) {
    JSONObject fresh = loadConfig();
    fresh.put("worker_heartbeat_ms", System.currentTimeMillis());
    boolean dirty = true;
    boolean sameOwner = fresh.optLong("active_chat_id", 0L) == cid && fresh.optLong("run_start_ms", 0L) == claimedRunStart;
    if (statusMsgId > 0L && sameOwner) {
        fresh.put("status_message_id", statusMsgId);
        fresh.put("last_ss_deleted", true);
    } else if (!statusIsMedia && statusMsgId > 0L && !sameOwner) {
        deleteOrphanedMsg = true;
    }
    JSONArray pendingNotices = fresh.optJSONArray("preempted_notices");
    if (pendingNotices != null && pendingNotices.length() > 0) {
        preemptNotices = pendingNotices;
        fresh.put("preempted_notices", new JSONArray());
    }
    if (fresh.has("crashed_notice")) {
        crashedNotice = fresh.optJSONObject("crashed_notice");
        fresh.remove("crashed_notice");
    }
    if (dirty) {
        saveConfig(fresh);
    }
    latestSnapshot = fresh;
}
if (deleteOrphanedMsg) {
    deleteStatus(cid, statusMsgId);
}
if (statusMsgId <= 0L) {
    String uDisp = formatUserDisplay(latestSnapshot, cid);
    appendAuditLog("FAIL", "INIT_STATUS_ERR", cid, uDisp, "mode=" + captureMode);
    if (adminId > 0L) {
        sendMsg(adminId, "⚠️ Failed to initialize status message for " + uDisp + " (mode=" + captureMode + ")", null);
    }
}
if (preemptNotices != null && preemptNotices.length() > 0) {
    String preemptSummary = recordPreemptedList(latestSnapshot, preemptNotices);
    notifyPreemptNotices(preemptNotices);
    if (preemptSummary.length() > 0 && adminId > 0L) {
        sendMsg(adminId, "ℹ️ VM Reset cancelled " + preemptNotices.length() + " pending request(s): " + preemptSummary, null);
    }
}
if (crashedNotice != null) {
    long cCid = crashedNotice.optLong("cid", 0L);
    String cUser = crashedNotice.optString("user_disp", "");
    String cDetail = crashedNotice.optString("detail", "");
    String cAlert = crashedNotice.optString("alert", "");
    appendAuditLog("FAIL", "QR_FAIL_CRASH_LEASE", cCid, cUser, cDetail);
    JSONArray targets = crashedNotice.optJSONArray("targets");
    if (targets != null) {
        for (int ti = 0; ti < targets.length(); ti++) {
            JSONObject t = targets.optJSONObject(ti);
            if (t == null) continue;
            notifyTargetFailure(t.optLong("chat_id", 0L), t.optLong("status_message_id", 0L), t.optBoolean("status_is_media", false), "❌ Previous request was interrupted. Please try again.", "⚠️ Interrupted • 🔄 Retry", false);
        }
    }
    if (cAlert.length() > 0 && adminId > 0L) {
        sendMsg(adminId, cAlert, null);
    }
}

long rem = 550L - (System.currentTimeMillis() - t0);
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
        "import java.text.SimpleDateFormat;\n"
        "import java.util.Date;\n"
        "import java.util.Locale;\n"
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
        + "\n\n"
        + _BSH_AUDIT_HELPERS
        + "\n\n"
        + _BSH_TIMING_HELPER
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

JSONObject uploadQrMultipart(long cid, long mid, byte[] pngBytes, String filename, String caption, String replyMarkupJson) {{
    boolean isEdit = (mid > 0L);
    String endpoint = isEdit ? "editMessageMedia" : "sendPhoto";
    JSONObject extra = new JSONObject();
    if (isEdit) {{
        JSONObject mediaObj = new JSONObject();
        mediaObj.put("type", "photo");
        mediaObj.put("media", "attach://photo");
        if (caption != null && caption.length() > 0) {{
            mediaObj.put("caption", caption);
        }}
        extra.put("media", mediaObj.toString());
    }} else if (caption != null && caption.length() > 0) {{
        extra.put("caption", caption);
    }}
    if (replyMarkupJson != null && replyMarkupJson.length() > 0) {{
        extra.put("reply_markup", replyMarkupJson);
    }}
    return postMultipartRaw(endpoint, cid, mid, extra, "photo", filename, "image/png", pngBytes, 15000);
}}

void setVisionState(JSONObject cfg, String st) {{
    String prev = cfg.optString("last_state", "");
    cfg.put("last_state", st);
    if (!st.equals(prev)) {{
        String tr = cfg.optString("state_trace", "");
        tr = (tr.length() > 0) ? (tr + ">" + st) : st;
        if (tr.length() > 180) {{
            int cut = tr.indexOf(">", tr.length() - 160);
            if (cut >= 0) tr = "..." + tr.substring(cut + 1);
            else tr = tr.substring(tr.length() - 160);
        }}
        cfg.put("state_trace", tr);
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
    setVisionState(cfg, "NO_SCREENSHOT");
    cfg.put("pending_status_text", "");
    saveConfig(cfg);
    return "WAIT";
}}

if (!latestReady) {{
    latestReady = hasValidImageTrailer(latest);
}}

logTiming("CAPTURE", (long) stepCount, System.currentTimeMillis() - waitStart);
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
    setVisionState(cfg, "TRUNCATED_SS");
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
    setVisionState(cfg, "DECODE_ERR");
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
        boolean isMedia = cfg.optBoolean("status_is_media", false);
        if (!isMedia && targetCid == adminId) {{
            return adminText;
        }}
        int cur = cfg.optInt("progress_pct", 0);
        if (userPct <= cur) {{
            return null;
        }}
        if (userPct > 100) userPct = 100;
        cfg.put("progress_pct", userPct);
        return isMedia ? formatButtonProgress(userPct) : formatProgress("⏳ Generating QR code...", userPct);
    }}
    void queueStepStatus(JSONObject cfg, String text) throws Exception {{
        if (text != null && text.length() > 0) {{
            cfg.put("pending_status_text", text);
        }} else {{
            cfg.put("pending_status_text", "");
        }}
    }}
    String prepareWaitNudge(JSONObject cfg, long targetCid, long adminId, int waitStep, int capPct) {{
        if (!cfg.optBoolean("status_is_media", false) && targetCid == adminId) return null;
        if (waitStep != 2 && waitStep != 5) return null;
        int nextPct = cfg.optInt("progress_pct", 0) + 10;
        if (nextPct > capPct) nextPct = capPct;
        return prepareStepStatus(cfg, targetCid, adminId, null, nextPct);
    }}
    String handleLoadingWait(JSONObject cfg, String countKey, String stateName, int maxWaits, int waitCapPct, long cid, long adminId) throws Exception {{
        int cnt = cfg.optInt(countKey, 0) + 1;
        cfg.put(countKey, cnt);
        setVisionState(cfg, stateName);
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
        setVisionState(cfg, "RESET_OPEN_RECENTS");
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

    // 1. Check VM Launcher vs VM Boot Loading (ignore pure-black pre-wake frames)
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
            cfg.put("vm_booting", true);
            cfg.put("vm_seen", true);
            cfg.put("other_count", 0);
            resetWaitCounters(cfg);
            setVisionState(cfg, "VM_LAUNCHER");
            String stepText = prepareStepStatus(cfg, cid, adminId, "🖥️ Entering Virtual Master...", 20);
            queueStepStatus(cfg, stepText);
            saveConfig(cfg);
            return "CLICK_ENTER";
        }}
        boolean isPureBlack = getR(360, 800) < 8 && getG(360, 800) < 8 && getB(360, 800) < 8
            && getR(100, 500) < 8 && getG(100, 500) < 8 && getB(100, 500) < 8
            && getR(360, 350) < 8 && getG(360, 350) < 8 && getB(360, 350) < 8
            && getR(627, 250) < 8 && getG(627, 250) < 8 && getB(627, 250) < 8;
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        if (!isPureBlack) {{
            cfg.put("vm_booting", true);
        }}
        setVisionState(cfg, isPureBlack ? "SCREEN_WAKING" : "VM_LOADING");
        String waitText = (!isPureBlack && (stepCount & 1) == 0)
            ? prepareWaitNudge(cfg, cid, adminId, 2, 20)
            : null;
        queueStepStatus(cfg, waitText);
        saveConfig(cfg);
        return "WAIT";
    }}

    // 2. Check Virtual Master 3x3 Floating Quick Menu Popup
    if (isPopupCorner(130, 590) && isPopupCorner(590, 590) &&
        isPopupCorner(130, 1050) && isPopupCorner(590, 1050) &&
        !(isDark(360, 350) && getB(360, 350) < 35)) {{
        cfg.put("vm_seen", true);
        setVisionState(cfg, "VM_POPUP");
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
        cfg.put("vm_seen", true);
        cfg.put("other_count", 0);
        cfg.put("reset_open_tries", 0);
        cfg.put("reset_recents_checked", true);
        resetWaitCounters(cfg);
        if (mode.equals("reset") && resetStage == 0) {{
            boolean hasCard = isRecentsCardPixel(360, 500) || isRecentsCardPixel(360, 800) || isRecentsCardPixel(360, 1000);
            if (hasCard && resetKills < 3) {{
                cfg.put("reset_kills", resetKills + 1);
                setVisionState(cfg, "VM_RECENTS");
                String stepText = prepareStepStatus(cfg, cid, adminId, "🔪 Closing Telcell Wallet...", 25);
                queueStepStatus(cfg, stepText);
                saveConfig(cfg);
                return "SWIPE_KILL_RECENT";
            }}
            cfg.put("reset_stage", 1);
            setVisionState(cfg, "VM_RECENTS_EMPTY");
            queueStepStatus(cfg, null);
            saveConfig(cfg);
            return "RESET_TO_HOME";
        }}
        setVisionState(cfg, "VM_RECENTS");
        queueStepStatus(cfg, null);
        saveConfig(cfg);
        return "RESET_TO_HOME";
    }}

    // 4. Check VM Home Screen (Telcell icon orange pixels)
    if (isDark(360, 800)) {{
        int o1 = 0;
        for (int x = 80; x <= 120; x += 3) {{
            for (int y = 360; y <= 400; y += 3) {{
                int c = bmp.getPixel(px(x), py(y));
                if (((c >> 16) & 0xFF) > 200 && ((c >> 8) & 0xFF) < 120 && (c & 0xFF) < 80) o1++;
            }}
        }}
        int o2 = 0;
        for (int x = 80; x <= 120; x += 3) {{
            for (int y = 120; y <= 165; y += 3) {{
                int c = bmp.getPixel(px(x), py(y));
                if (((c >> 16) & 0xFF) > 200 && ((c >> 8) & 0xFF) < 120 && (c & 0xFF) < 80) o2++;
            }}
        }}
        if (o1 >= 15 || o2 >= 15) {{
            cfg.put("vm_booting", false);
            cfg.put("vm_seen", true);
            cfg.put("other_count", 0);
            cfg.put("reset_open_tries", 0);
            resetWaitCounters(cfg);
            if (mode.equals("reset") && resetStage == 0 && !resetRecentsChecked && resetKills == 0) {{
                cfg.put("reset_recents_checked", true);
                setVisionState(cfg, "RESET_CHECK_RECENTS");
                String stepText = prepareStepStatus(cfg, cid, adminId, "🧹 Checking running VM apps...", 20);
                queueStepStatus(cfg, stepText);
                saveConfig(cfg);
                return "OPEN_RECENTS";
            }}
            if (mode.equals("reset")) {{
                cfg.put("reset_stage", 2);
            }}
            setVisionState(cfg, (o1 >= 15) ? "VM_HOME_1" : "VM_HOME_2");
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
        cfg.put("vm_seen", true);
        if (mode.equals("reset")) {{
            cfg.put("qr_was_closed", true);
            setVisionState(cfg, "RESET_CLOSE_QR");
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
                setVisionState(cfg, "STALE_QR");
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
                setVisionState(cfg, "RESET_CLOSE_QR");
                cfg.put("other_count", 0);
                resetWaitCounters(cfg);
                queueStepStatus(cfg, null);
                saveConfig(cfg);
                return "CLOSE_MODAL";
            }}
            statusMsgId = cfg.optLong("status_message_id", 0L);
            String activeTrig = cfg.optString("active_trigger", cfg.optBoolean("status_is_media", false) ? "callback_media" : "cmd");
            long activeStartMs = cfg.optLong("active_start_ms", cfg.optLong("run_start_ms", 0L));
            int snapOther = cfg.optInt("other_count", 0);
            int snapWhite = cfg.optInt("white_count", 0);
            int snapLoad = cfg.optInt("loading_count", 0);
            queueStepStatus(cfg, null);
            int cx = px(130);
            int cy = py(445);
            int cw = px(590) - cx;
            int ch = py(905) - cy;
            Bitmap qrBmp = Bitmap.createBitmap(bmp, cx, cy, cw, ch);
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            qrBmp.compress(Bitmap.CompressFormat.PNG, 100, baos);
            qrBmp.recycle();
            boolean statusIsMedia = cfg.optBoolean("status_is_media", false);
            long targetEditMid = (statusIsMedia && statusMsgId > 0L) ? statusMsgId : 0L;
            String ts = new SimpleDateFormat("HH:mm:ss", Locale.US).format(new Date());
            String caption = "🎫 QR Code • " + ts + " (valid ~30s)";
            String qrMarkup = makeInlineButtonMarkup("🔄 Refresh QR", "/qr").toString();
            boolean usedFallback = false;
            JSONObject upRes = uploadQrMultipart(cid, targetEditMid, baos.toByteArray(), "qr.png", caption, qrMarkup);
            int code = upRes.optInt("code", -1);
            String lastUploadDesc = upRes.optString("desc", "");
            if (targetEditMid > 0L && code >= 400 && code < 500) {{
                usedFallback = true;
                upRes = uploadQrMultipart(cid, 0L, baos.toByteArray(), "qr.png", caption, qrMarkup);
                code = upRes.optInt("code", -1);
                lastUploadDesc = upRes.optString("desc", "");
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
                        boolean nextIsMedia = nextItem.optBoolean("status_is_media", false);
                        long prevStart = cfg.optLong("run_start_ms", 0L);
                        long nextRunStart = (nowMs > prevStart) ? nowMs : (prevStart + 1L);
                        cfg.put("_pop_queue", true);
                        cfg.put("queue", rem);
                        cfg.put("active_chat_id", popNextCid);
                        cfg.put("status_message_id", popNextMid);
                        cfg.put("status_is_media", nextIsMedia);
                        cfg.put("run_start_ms", nextRunStart);
                        cfg.put("active_start_ms", nextRunStart);
                        cfg.put("active_trigger", nextItem.optString("trigger", nextIsMedia ? "queued_media" : "queued_cmd"));
                        cfg.put("qr_was_closed", true);
                        cfg.put("step_count", 2);
                        cfg.put("other_count", 0);
                        resetWaitCounters(cfg);
                        cfg.put("busy_until", nowMs + 45000L);
                        cfg.put("worker_heartbeat_ms", nowMs);
                        cfg.put("last_state", "NEXT_IN_QUEUE");
                        cfg.put("state_trace", "NEXT_IN_QUEUE");
                        cfg.put("progress_pct", (popNextCid == adminId && !nextIsMedia) ? 0 : 70);
                        if (!statusIsMedia && code == 200 && cid > 0L && statusMsgId > 0L) {{
                            cfg.put("pending_delete_cid", cid);
                            cfg.put("pending_delete_mid", statusMsgId);
                        }}
                        nextText = nextIsMedia
                            ? formatButtonProgress(70)
                            : ((popNextCid == adminId)
                                ? "🔄 Generating QR code for your request..."
                                : formatProgress("⏳ Generating QR code...", 70));
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
                        cfg.put("status_is_media", false);
                        cfg.put("progress_pct", 0);
                        resetWaitCounters(cfg);
                        saveConfig(cfg);
                    }}
                }}
            }}
            long doneMs = System.currentTimeMillis();
            long elapsedMs = (activeStartMs > 0L && doneMs >= activeStartMs) ? (doneMs - activeStartMs) : 0L;
            String baseTrace = cfg.optString("state_trace", "");
            if (code == 200) {{
                if (!hasNext && !statusIsMedia) {{
                    deleteStatus(cid, statusMsgId);
                }}
                String finTrace = (baseTrace.length() > 0) ? (baseTrace + ">QR_SENT") : "QR_SENT";
                recordUsageSafe(cid, "ok", elapsedMs, usedFallback ? "QR_SENT_FALLBACK" : "QR_SENT", "");
                appendAuditLog("OK", "QR_SENT", cid, formatUserDisplay(cfg, cid),
                    "trigger=" + activeTrig + " steps=" + stepCount + " elapsed=" + formatSec(elapsedMs)
                    + (usedFallback ? " fallback=sendPhoto" : "") + " trace=" + finTrace);
            }} else {{
                String errText = (cid == adminId)
                    ? "❌ Failed to upload QR (HTTP " + code + ")."
                    : "❌ Failed to upload QR. Please try again.";
                notifyTargetFailure(cid, statusMsgId, statusIsMedia, errText, "⚠️ Failed • 🔄 Retry", false);
                String reasonDesc = "QR upload failed (HTTP " + code + ")" + (lastUploadDesc.length() > 0 ? (": " + lastUploadDesc) : "");
                String finTrace = (baseTrace.length() > 0) ? (baseTrace + ">QR_ERR") : "QR_ERR";
                recordUsageSafe(cid, "fail", elapsedMs, "UPLOAD_HTTP_" + code, lastUploadDesc);
                appendAuditLog("FAIL", "QR_FAIL_UPLOAD", cid, formatUserDisplay(cfg, cid),
                    reasonDesc + " trigger=" + activeTrig + " steps=" + stepCount + " elapsed=" + formatSec(elapsedMs) + " trace=" + finTrace);
                if (adminId > 0L) {{
                    sendMsg(adminId,
                        buildFailureAlert(cfg, "🚨 QR Upload Failed", cid, activeTrig, reasonDesc, elapsedMs, stepCount, "QR_MODAL", finTrace, snapOther, snapWhite, snapLoad, ""),
                        null);
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
                int c = bmp.getPixel(px(x), py(y));
                if (((c >> 16) & 0xFF) > 200 && ((c >> 8) & 0xFF) < 130 && (c & 0xFF) < 100) pinLogo++;
            }}
        }}
        if (pinLogo >= 10) {{
            cfg.put("vm_booting", false);
            cfg.put("vm_seen", true);
            if (mode.equals("reset") && resetStage == 0) {{
                return handleResetInApp(cfg, cid, adminId);
            }}
            int spinner = 0;
            for (int x = 330; x <= 390; x += 3) {{
                for (int y = 680; y <= 715; y += 3) {{
                    int c = bmp.getPixel(px(x), py(y));
                    if (((c >> 16) & 0xFF) > 215 && (c & 0xFF) < 120) spinner++;
                }}
            }}
            if (spinner >= 3) {{
                cfg.put("white_count", 0);
                return handleLoadingWait(cfg, "loading_count", "PIN_SPINNER", 9, 40, cid, adminId);
            }}
            setVisionState(cfg, "PIN_PAD");
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
        cfg.put("vm_seen", true);
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
                int c = bmp.getPixel(px(x), py(y));
                int g = (c >> 8) & 0xFF;
                if (((c >> 16) & 0xFF) > 200 && g >= 70 && g <= 165 && (c & 0xFF) < 125) svcLow++;
            }}
            for (int y = 785; y <= 845; y += 6) {{
                int c = bmp.getPixel(px(x), py(y));
                int g = (c >> 8) & 0xFF;
                if (((c >> 16) & 0xFF) > 200 && g >= 70 && g <= 165 && (c & 0xFF) < 125) svcHigh++;
            }}
        }}
        if (svcLow < 3 && svcHigh < 3 && cfg.optInt("loading_count", 0) < 5) {{
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 9, 50, cid, adminId);
        }}
        boolean useLow = (svcLow >= 3) || (svcHigh < 3 && isWhite(360, 1100) && !isWhite(360, 800));
        String prevDashState = cfg.optString("last_state", "");
        if (prevDashState.equals(useLow ? "DASHBOARD_LOW" : "DASHBOARD_HIGH")) {{
            // Transport row was just tapped; give the page one short tick to navigate.
            setVisionState(cfg, "DASH_OPENING");
            saveConfig(cfg);
            return "WAIT";
        }}
        if (!useLow && cfg.optInt("loading_count", 0) < 3) {{
            // The HIGH Услуги row is often transient: lazy-loaded promo cards push it down
            // right after the PIN. Wait briefly for the layout to settle before tapping.
            cfg.put("white_count", 0);
            return handleLoadingWait(cfg, "loading_count", "DASH_LOADING", 9, 50, cid, adminId);
        }}
        cfg.put("qr_was_closed", true);
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        setVisionState(cfg, useLow ? "DASHBOARD_LOW" : "DASHBOARD_HIGH");
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
        cfg.put("vm_seen", true);
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
            long rstStartMs = cfg.optLong("active_start_ms", cfg.optLong("run_start_ms", 0L));
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
                    boolean nextIsMedia = nextItem.optBoolean("status_is_media", false);
                    long prevStart = latestCfg.optLong("run_start_ms", cfg.optLong("run_start_ms", 0L));
                    long nextRunStart = (nowMs > prevStart) ? nowMs : (prevStart + 1L);
                    cfg.put("_pop_queue", true);
                    cfg.put("queue", rem);
                    cfg.put("capture_mode", "qr");
                    cfg.put("active_chat_id", popNextCid);
                    cfg.put("status_message_id", popNextMid);
                    cfg.put("status_is_media", nextIsMedia);
                    cfg.put("run_start_ms", nextRunStart);
                    cfg.put("active_start_ms", nextRunStart);
                    cfg.put("active_trigger", nextItem.optString("trigger", nextIsMedia ? "queued_media" : "queued_cmd"));
                    cfg.put("step_count", 2);
                    cfg.put("reset_stage", 0);
                    cfg.put("reset_kills", 0);
                    cfg.put("reset_recents_checked", false);
                    cfg.put("reset_open_tries", 0);
                    cfg.put("reset_notified", false);
                    cfg.put("busy_until", nowMs + 45000L);
                    cfg.put("worker_heartbeat_ms", nowMs);
                    cfg.put("last_state", "TICKET_LIST");
                    cfg.put("state_trace", "TICKET_LIST");
                    cfg.put("progress_pct", (popNextCid == adminId && !nextIsMedia) ? 0 : 80);
                    String nextText = nextIsMedia
                        ? formatButtonProgress(80)
                        : ((popNextCid == adminId)
                            ? "🎫 Selecting ticket..."
                            : formatProgress("⏳ Generating QR code...", 80));
                    queueStepStatus(cfg, nextText);
                    saveConfig(cfg);
                    hasNext = true;
                }} else {{
                    queueStepStatus(cfg, null);
                }}
            }}
            long rstNow = System.currentTimeMillis();
            long rstElapsed = (rstStartMs > 0L && rstNow >= rstStartMs) ? (rstNow - rstStartMs) : 0L;
            appendAuditLog("ADMIN", "RESET_DONE", cid, formatUserDisplay(cfg, cid),
                "steps=" + stepCount + " elapsed=" + formatSec(rstElapsed) + " queued_handoff=" + hasNext);
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
        if (cfg.optString("last_state", "").equals("TICKET_LIST")) {{
            // The row was just tapped; the QR modal may still be opening. Wait one
            // short tick instead of tapping the row a second time.
            setVisionState(cfg, "TICKET_OPENING");
            saveConfig(cfg);
            return "WAIT";
        }}
        setVisionState(cfg, "TICKET_LIST");
        cfg.put("other_count", 0);
        resetWaitCounters(cfg);
        String stepText = prepareStepStatus(cfg, cid, adminId, "🎫 Selecting ticket...", 80);
        queueStepStatus(cfg, stepText);
        cfg.put("row_tap_ms", System.currentTimeMillis());
        saveConfig(cfg);
        return "CLICK_TICKET_ROW";
    }}

    // 9b. Check Telcell Buy Ticket Tab (Проездной билет -> Купить билет)
    boolean buyTabOrange = isOrange(100, 235) && isWhite(277, 235);
    boolean buyCardBtns = isWhite(360, 120) && isWhite(277, 235) && isOrange(550, 485);
    if (buyTabOrange || buyCardBtns) {{
        cfg.put("vm_booting", false);
        cfg.put("vm_seen", true);
        if (mode.equals("reset") && resetStage == 0) {{
            return handleResetInApp(cfg, cid, adminId);
        }}
        cfg.put("qr_was_closed", true);
        setVisionState(cfg, "BUY_TICKET_TAB");
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
    long rowTapAge = System.currentTimeMillis() - cfg.optLong("row_tap_ms", 0L);
    if (cfg.optLong("row_tap_ms", 0L) > 0L && rowTapAge < 6000L) {{
        // Telcell is still opening the QR after the row tap; do not count these
        // frames toward CLICK_BACK/RESET_TO_HOME recovery (back would close the QR).
        setVisionState(cfg, "QR_OPENING");
        saveConfig(cfg);
        return "WAIT";
    }}
    int otherCount = cfg.optInt("other_count", 0) + 1;
    cfg.put("other_count", otherCount);
    setVisionState(cfg, "OTHER");
    resetWaitCounters(cfg);
    queueStepStatus(cfg, null);
    saveConfig(cfg);
    if (!cfg.optBoolean("vm_seen", false) && !cfg.optBoolean("vm_launched", false) && otherCount == 2) {{
        cfg.put("vm_booting", false);
        cfg.put("vm_launched", true);
        cfg.put("other_count", 0);
        saveConfig(cfg);
        return "LAUNCH_VM";
    }}
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
        + "\n\n"
        + _BSH_TIMING_HELPER
        + """

long t0 = System.currentTimeMillis();
long waitMs = 350L;
if (stepCmd.equals("WAIT")) waitMs = 180L;
else if (stepCmd.equals("DISMISS_POPUP")) waitMs = 350L;
else if (stepCmd.equals("CLOSE_MODAL") || stepCmd.equals("CLICK_BACK") || stepCmd.equals("RESET_TO_HOME")) waitMs = 450L;
else if (stepCmd.equals("OPEN_RECENTS") || stepCmd.equals("SWIPE_KILL_RECENT")) waitMs = 550L;
else if (stepCmd.equals("CLICK_AVAILABLE_TAB")) waitMs = 700L;
else if (stepCmd.equals("CLICK_TRANSPORT_LOW") || stepCmd.equals("CLICK_TRANSPORT_HIGH")) waitMs = 750L;
else if (stepCmd.equals("ENTER_PIN")) waitMs = 850L;
else if (stepCmd.equals("CLICK_ENTER") || stepCmd.equals("LAUNCH_VM")) waitMs = 900L;
else if (stepCmd.equals("CLICK_TICKET_ROW")) waitMs = 520L;
else if (stepCmd.equals("LAUNCH_1") || stepCmd.equals("LAUNCH_2")) waitMs = 1100L;

long cid = 0L;
long mid = 0L;
long delCid = 0L;
long delMid = 0L;
boolean statusIsMedia = false;
String pendingText = "";
synchronized (System.class) {
    JSONObject cfg = loadConfig();
    if (stepCmd.equals("WAIT") && cfg.optString("last_state", "").equals("SCREEN_WAKING")
        && cfg.optInt("step_count", 0) <= 2) {
        // The first capture already blocked for the display to unblock.
        waitMs = 80L;
    } else if (stepCmd.equals("WAIT") && cfg.optBoolean("vm_booting", false)) {
        waitMs = 500L;
    }
    if (cfg.has("active_chat_id") || cfg.optBoolean("worker_active", false)) {
        cfg.put("worker_heartbeat_ms", System.currentTimeMillis());
        delCid = cfg.optLong("pending_delete_cid", 0L);
        delMid = cfg.optLong("pending_delete_mid", 0L);
        if (delCid > 0L && delMid > 0L) {
            cfg.put("pending_delete_cid", 0L);
            cfg.put("pending_delete_mid", 0L);
        }
        pendingText = cfg.optString("pending_status_text", "");
        if (pendingText.length() > 0) {
            cid = cfg.optLong("active_chat_id", 0L);
            mid = cfg.optLong("status_message_id", 0L);
            statusIsMedia = cfg.optBoolean("status_is_media", false);
            if (mid > 0L) {
                cfg.put("pending_status_text", "");
            }
        }
        saveConfig(cfg);
    }
}
if (delCid > 0L && delMid > 0L) {
    deleteStatus(delCid, delMid);
}
if (pendingText.length() > 0 && mid > 0L) {
    if (statusIsMedia) {
        editButton(cid, mid, pendingText, "noop");
    } else {
        updateStatus(cid, mid, pendingText);
    }
}

long rem = waitMs - (System.currentTimeMillis() - t0);
if (rem > 0L) {
    try {
        Thread.sleep(rem);
    } catch (Exception e) {
    }
}
logTiming("POST_" + stepCmd, waitMs, System.currentTimeMillis() - t0);
return "OK";
"""
    )


def build_timeout_script() -> str:
    """BeanShell Java 7 post-loop guard to clear busy lock and report timeouts."""
    return (
        "import java.io.*;\n"
        "import java.net.HttpURLConnection;\n"
        "import java.net.URL;\n"
        "import java.text.SimpleDateFormat;\n"
        "import java.util.Date;\n"
        "import java.util.Locale;\n"
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
        + "\n\n"
        + _BSH_AUDIT_HELPERS
        + """

if (stepCmd.equals("ABORT_PREEMPTED")) return "KEEP_ON";

boolean keepScreenOn = false;
boolean notifyCleanup = false;
boolean resetAlreadyNotified = false;
boolean statusIsMedia = false;
long adminId = 0L;
long cid = 0L;
long mid = 0L;
long activeStartMs = 0L;
String activeTrigger = "cmd";
String lastState = "UNKNOWN";
String stateTrace = "";
int stepCount = 0;
int otherCount = 0;
int whiteCount = 0;
int loadingCount = 0;
JSONArray queue = null;
JSONObject cfgSnap = new JSONObject();

synchronized (System.class) {
    File f = new File(configPath);
    if (f.exists()) {
        FileInputStream fis = new FileInputStream(f);
        String raw = readStream(fis);
        fis.close();
        if (raw.length() > 0) {
            JSONObject cfg = new JSONObject(raw);
            cfgSnap = cfg;
            adminId = cfg.optLong("admin_id", 0L);
            long busyUntil = cfg.optLong("busy_until", 0L);
            boolean workerActive = cfg.optBoolean("worker_active", false);
            resetAlreadyNotified = cfg.optBoolean("reset_notified", false);
            statusIsMedia = cfg.optBoolean("status_is_media", false);
            cid = cfg.optLong("active_chat_id", 0L);
            mid = cfg.optLong("status_message_id", 0L);
            activeStartMs = cfg.optLong("active_start_ms", cfg.optLong("run_start_ms", 0L));
            activeTrigger = cfg.optString("active_trigger", statusIsMedia ? "callback_media" : "cmd");
            lastState = cfg.optString("last_state", "UNKNOWN");
            stateTrace = cfg.optString("state_trace", "");
            stepCount = cfg.optInt("step_count", 0);
            otherCount = cfg.optInt("other_count", 0);
            whiteCount = cfg.optInt("white_count", 0);
            loadingCount = cfg.optInt("loading_count", 0);

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
                    cfg.put("status_is_media", false);
                    cfg.put("media_init_pending", false);
                    cfg.put("pending_cb_id", "");
                    cfg.put("state_trace", "");
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
    long nowMs = System.currentTimeMillis();
    long elapsedMs = (activeStartMs > 0L && nowMs >= activeStartMs) ? (nowMs - activeStartMs) : 0L;
    boolean isResetDone = stepCmd.equals("DONE_RESET");
    String msg = isResetDone
        ? "✅ VM app reset complete — Telcell restarted & ready."
        : (cid == adminId
            ? "❌ Timed out waiting for QR screen (last state: " + lastState + "). Please try again."
            : "❌ Timed out generating QR code. Please try again.");
    String retryBtn = isResetDone ? "✅ Reset done • 🔄 Refresh" : "❌ Timed out • 🔄 Retry";
    notifyTargetFailure(cid, mid, statusIsMedia, msg, retryBtn, true);

    if (isResetDone) {
        if (cid > 0L) {
            appendAuditLog("ADMIN", "RESET_DONE", cid, formatUserDisplay(cfgSnap, cid),
                "steps=" + stepCount + " elapsed=" + formatSec(elapsedMs) + " trace=" + stateTrace);
        }
    } else {
        String reasonStr = stepCmd.equals("ABORT_TIMEOUT")
            ? ("Timed out waiting for QR screen (step cap " + stepCount + ")")
            : ("Loop ended before QR (" + stepCmd + ", step " + stepCount + ")");
        if (cid != 0L) {
            recordUsageSafe(cid, "fail", elapsedMs, "TIMEOUT_" + lastState, reasonStr);
            appendAuditLog("FAIL", "QR_FAIL_TIMEOUT", cid, formatUserDisplay(cfgSnap, cid),
                reasonStr + " trigger=" + activeTrigger + " state=" + lastState
                + " elapsed=" + formatSec(elapsedMs) + " trace=" + stateTrace);
        }
    }

    String failedQueueSummary = "";
    if (queue != null) {
        String qMsg = isResetDone
            ? "❌ Request cancelled by VM reset. Please try again."
            : "❌ Previous request timed out. Please try again.";
        String qBtn = isResetDone ? "❌ Cancelled • 🔄 Retry" : "❌ Timed out • 🔄 Retry";
        for (int qi = 0; qi < queue.length(); qi++) {
            JSONObject qItem = queue.optJSONObject(qi);
            if (qItem != null) {
                long qCid = qItem.optLong("chat_id", 0L);
                long qMid = qItem.optLong("status_message_id", 0L);
                boolean qMedia = qItem.optBoolean("status_is_media", false);
                long qEnqMs = qItem.optLong("enqueued_ms", activeStartMs);
                long qElapsed = (qEnqMs > 0L && nowMs >= qEnqMs) ? (nowMs - qEnqMs) : elapsedMs;
                notifyTargetFailure(qCid, qMid, qMedia, qMsg, qBtn, true);
                if (!isResetDone && qCid != 0L) {
                    String qDisp = formatUserDisplay(cfgSnap, qCid);
                    recordUsageSafe(qCid, "fail", qElapsed, "QUEUED_TIMEOUT", "upstream=" + lastState);
                    appendAuditLog("FAIL", "QR_FAIL_QUEUED_TIMEOUT", qCid, qDisp,
                        "upstream=" + lastState + " step=" + stepCount + " elapsed=" + formatSec(qElapsed));
                    if (failedQueueSummary.length() > 0) {
                        failedQueueSummary = failedQueueSummary + ", ";
                    }
                    failedQueueSummary = failedQueueSummary + qDisp;
                }
            }
        }
    }

    if (!isResetDone && adminId > 0L) {
        String reasonLabel = stepCmd.equals("ABORT_TIMEOUT")
            ? "Timed out waiting for QR screen (max steps reached)"
            : ("Timed out / loop exited (" + stepCmd + ")");
        String adminAlert = buildFailureAlert(
            cfgSnap,
            "🚨 QR Request Failed",
            cid,
            activeTrigger,
            reasonLabel,
            elapsedMs,
            stepCount,
            lastState,
            stateTrace,
            otherCount,
            whiteCount,
            loadingCount,
            failedQueueSummary
        );
        sendMsg(adminId, adminAlert, null);
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
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"callback_query":{"id":""',
            r'"callback_query":\s*\{[^}]{0,120}"id":\s*"([^"]{0,80})"',
            "callback_id",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"data":""',
            r'"data":\s*"([^"]{0,100})"',
            "callback_data",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"message":{"message_id":0',
            r'"message":\s*\{[^}]{0,80}"message_id":\s*(\d+)',
            "callback_msg_id",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"from":{"id":0,"is_bot":false,"first_name":""',
            r'"from":\s*\{[^}]{0,220}"is_bot":\s*false[^}]{0,220}"first_name":\s*"([^"\\]{0,64})"',
            "sender_name",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"from":{"id":0,"is_bot":false,"username":""',
            r'"from":\s*\{[^}]{0,220}"is_bot":\s*false[^}]{0,220}"username":\s*"([^"\\]{0,64})"',
            "sender_username",
        )
    )
    actions.append(
        make_extract_text(
            sg,
            '{lv=webhook_body}\n"sender_user":{"id":0',
            r'"(?:sender_user|forward_from)":\s*\{\s*"id":\s*(-?\d+)',
            "forward_user_id",
        )
    )

    # 2. JavaAction #1: Telegram Router, Auth & Command Handler
    actions.append(
        make_java_action(sg, build_router_script(), response_var="bot_action")
    )

    # 3. If bot_action == "RUN": wake screen directly onto running VM and overlap initial status send
    actions.append(make_if_var_equals(sg, "bot_action", "RUN"))
    actions.append(make_screen_on(sg, screen_off=False))
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
    add_cmd_branch(
        "LAUNCH_VM",
        [make_launch_app(sg, "Virtual Master", "com.clone.android.dual.space")],
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
            pin_actions.append(make_pause(sg, millis=250))
    add_cmd_branch("ENTER_PIN", pin_actions)

    add_cmd_branch("CLICK_TRANSPORT_LOW", [make_click_xy(sg, 360, 1100)])
    add_cmd_branch("CLICK_TRANSPORT_HIGH", [make_click_xy(sg, 360, 840)])
    add_cmd_branch("CLICK_AVAILABLE_TAB", [make_click_xy(sg, 277, 200)])
    add_cmd_branch("CLICK_TICKET_ROW", [make_click_xy(sg, 360, 400)])
    add_cmd_branch("CLOSE_MODAL", [make_click_xy(sg, 626, 121)])
    add_cmd_branch("CLICK_BACK", [make_click_xy(sg, 151, 1553)])
    add_cmd_branch("RESET_TO_HOME", [make_click_xy(sg, 360, 1553)])

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
        make_var("callback_data", supports_input=False),
        make_var("callback_id", supports_input=False),
        make_var("callback_msg_id", supports_input=False),
        make_var("chat_id", supports_input=False),
        make_var("forward_user_id", supports_input=False),
        make_var("msg_text", supports_input=False),
        make_var("pin_d1", supports_input=False),
        make_var("pin_d2", supports_input=False),
        make_var("pin_d3", supports_input=False),
        make_var("pin_d4", supports_input=False),
        make_var("screen_action"),
        make_var("sender_name", supports_input=False),
        make_var("sender_username", supports_input=False),
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
