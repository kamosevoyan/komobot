#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

read_env_default() {
	local key="$1"
	if [[ -f "$SCRIPT_DIR/.env" ]]; then
		grep -E "^${key}=" "$SCRIPT_DIR/.env" | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r' || true
	fi
}

prompt_var() {
	local var_name="$1"
	local label="$2"
	local default_val="$3"
	local is_secret="${4:-0}"
	local input_val="${!var_name:-}"

	if [[ -z "$input_val" && -t 0 ]]; then
		local hint="required"
		if [[ -n "$default_val" ]]; then
			if [[ "$is_secret" == "1" ]]; then
				hint="Enter to keep .env default"
			else
				hint="default: $default_val"
			fi
		fi
		read -r -p "Enter $label ($hint): " input_val
	fi

	if [[ -z "$input_val" ]]; then
		input_val="$default_val"
	fi
	if [[ -z "$input_val" ]]; then
		echo "Error: $label is required." >&2
		exit 1
	fi
	printf -v "$var_name" '%s' "$input_val"
}

DEFAULT_BOT_TOKEN="$(read_env_default BOT_TOKEN)"
DEFAULT_ADMIN_ID="$(read_env_default ADMIN_ID)"
DEFAULT_APP_PIN="$(read_env_default APP_PIN)"
DEFAULT_APP_NAME="$(read_env_default APP_NAME)"

BOT_TOKEN_VAL="${BOT_TOKEN:-}"
ADMIN_ID_VAL="${ADMIN_ID:-}"
APP_PIN_VAL="${APP_PIN:-}"
APP_NAME_VAL="${APP_NAME:-}"

prompt_var BOT_TOKEN_VAL "BOT_TOKEN" "$DEFAULT_BOT_TOKEN" 1
prompt_var ADMIN_ID_VAL "ADMIN_ID" "$DEFAULT_ADMIN_ID" 0
prompt_var APP_PIN_VAL "APP_PIN" "$DEFAULT_APP_PIN" 1
prompt_var APP_NAME_VAL "APP_NAME" "$DEFAULT_APP_NAME" 0

echo "==> Generating Komobot_Controller.macro..."
python3 "$SCRIPT_DIR/generate_macro.py" \
	--bot-token "$BOT_TOKEN_VAL" \
	--admin-id "$ADMIN_ID_VAL" \
	--app-pin "$APP_PIN_VAL" \
	--app-name "$APP_NAME_VAL"

echo "==> Checking ADB device..."
adb wait-for-device
adb get-state

echo "==> Granting MacroDroid permissions..."
for perm in \
	android.permission.WRITE_SECURE_SETTINGS \
	android.permission.WRITE_GLOBAL_SETTINGS \
	android.permission.READ_LOGS \
	android.permission.DUMP; do
	if adb shell pm grant com.arlosoft.macrodroid "$perm" 2>/dev/null; then
		echo "  granted $perm"
	else
		echo "  skipped/unchanged $perm"
	fi
done

for op in MANAGE_EXTERNAL_STORAGE SYSTEM_ALERT_WINDOW; do
	if adb shell appops set com.arlosoft.macrodroid "$op" allow 2>/dev/null; then
		echo "  appops allowed $op"
	else
		echo "  appops skipped $op"
	fi
done

echo "==> Configuring Doze, Wi-Fi sleep, screen timeout & lockscreen..."
for pkg in com.arlosoft.macrodroid com.clone.android.dual.space; do
	adb shell dumpsys deviceidle whitelist "+$pkg" >/dev/null 2>&1 || true
	for op in RUN_IN_BACKGROUND RUN_ANY_IN_BACKGROUND WAKE_LOCK; do
		adb shell appops set "$pkg" "$op" allow 2>/dev/null || true
	done
done
adb shell appops set com.clone.android.dual.space TOAST_WINDOW deny 2>/dev/null || true
adb shell dumpsys deviceidle disable >/dev/null 2>&1 || true
adb shell settings put global app_standby_enabled 0 2>/dev/null || true
adb shell settings put global settings_enable_monitor_phantom_procs false 2>/dev/null || true
adb shell cmd device_config override activity_manager max_phantom_processes 2147483647 2>/dev/null || adb shell cmd device_config put activity_manager max_phantom_processes 2147483647 2>/dev/null || true
adb shell settings put global wifi_power_save 0 2>/dev/null || true
adb shell settings put global wifi_sleep_policy 2 2>/dev/null || true
adb shell settings put system screen_off_timeout 120000 2>/dev/null || true
adb shell locksettings set-disabled true 2>/dev/null || true
adb shell settings put secure lockscreen.disabled 1 2>/dev/null || true
adb shell settings put secure lock_screen_lock_after_timeout 86400000 2>/dev/null || true

adb shell settings put system enable_smart_capture 0 2>/dev/null || true
adb shell settings put global window_animation_scale 0 2>/dev/null || true
adb shell settings put global transition_animation_scale 0 2>/dev/null || true
adb shell settings put global animator_duration_scale 0 2>/dev/null || true

echo "==> Preparing screenshot workspace & cleaning old screenshots..."
adb shell 'mkdir -p /storage/emulated/0/komobot_ss && touch /storage/emulated/0/komobot_ss/.nomedia && rm -f /storage/emulated/0/komobot_ss/frame.png /storage/emulated/0/komobot_ss/frame.jpg'
adb shell 'rm -f /storage/emulated/0/DCIM/Screenshots/*Virtual\ Master* /storage/emulated/0/DCIM/Screenshots/.trashed-* /storage/emulated/0/DCIM/Screenshots/thumbnail_* /storage/emulated/0/DCIM/Screenshots/*Virtual_Master* /storage/emulated/0/Pictures/Screenshots/*Virtual\ Master* 2>/dev/null || true'

echo "==> Seeding /storage/emulated/0/Download/komobot_config.json if absent..."
if ! adb shell "[ -f /storage/emulated/0/Download/komobot_config.json ]"; then
	TMP_CFG="$(mktemp)"
	cat >"$TMP_CFG" <<EOF
{
  "admin_id": $ADMIN_ID_VAL,
  "allowed_users": [
    $ADMIN_ID_VAL,
    879155028
  ],
  "public_access": true,
  "busy_until": 0,
  "last_update_id": 0
}
EOF
	adb push "$TMP_CFG" /storage/emulated/0/Download/komobot_config.json
	rm -f "$TMP_CFG"
else
	echo "  komobot_config.json already exists on device, preserving."
fi

echo "==> Pushing Komobot_Controller.macro to phone..."
adb push "$SCRIPT_DIR/Komobot_Controller.macro" /storage/emulated/0/Download/Komobot_Controller.macro

echo "==> Waking screen and opening macro in MacroDroid..."
adb shell "input keyevent 224; wm dismiss-keyguard 2>/dev/null || true; sleep 0.4; input swipe 360 1200 360 300; cmd statusbar collapse 2>/dev/null || true; am start -a android.intent.action.VIEW -d file:///storage/emulated/0/Download/Komobot_Controller.macro -n com.arlosoft.macrodroid/.filehandler.FileHandlerProxy"

tap_ui_node() {
	local pattern="$1"
	local xml
	xml="$(adb shell "uiautomator dump /data/local/tmp/md_ui.xml >/dev/null && cat /data/local/tmp/md_ui.xml" 2>/dev/null || true)"
	local coords
	coords="$(python3 -c '
import re, sys, xml.etree.ElementTree as ET
xml_str = sys.stdin.read()
idx = xml_str.find("<hierarchy")
if idx < 0:
    sys.exit(1)
root = ET.fromstring(xml_str[idx:])
pat = sys.argv[1].lower()
for node in root.iter("node"):
    rid = node.attrib.get("resource-id", "").lower()
    txt = node.attrib.get("text", "").lower()
    desc = node.attrib.get("content-desc", "").lower()
    if pat == rid or pat == txt or pat == desc or pat in rid:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            print((x1 + x2) // 2, (y1 + y2) // 2)
            sys.exit(0)
sys.exit(1)
' "$pattern" <<<"$xml" 2>/dev/null || true)"
	if [[ -n "$coords" ]]; then
		adb shell input tap $coords
		return 0
	fi
	return 1
}

accepted=0
for _ in 1 2 3; do
	sleep 2
	if tap_ui_node "com.arlosoft.macrodroid:id/acceptButton"; then
		echo "  Tapped Add Macro (acceptButton)"
		accepted=1
		break
	fi
done
if [[ "$accepted" -eq 0 ]]; then
	echo "  acceptButton not found via UI dump, tapping fallback (637, 1337)"
	adb shell input tap 637 1337
fi

for _ in 1 2; do
	sleep 1.5
	if tap_ui_node "OVERWRITE"; then
		echo "  Confirmed OVERWRITE existing macro"
		break
	elif tap_ui_node "Import Macro"; then
		echo "  Import Macro dialog detected, tapping OVERWRITE fallback (537, 868)"
		adb shell input tap 537 868
		break
	fi
done

sleep 1
adb shell rm -f /storage/emulated/0/Download/Komobot_Controller.macro /data/local/tmp/md_ui.xml
echo "==> Done deploying Komobot_Controller.macro to MacroDroid."
