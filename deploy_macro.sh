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
DEFAULT_ADMIN_BOT_TOKEN="$(read_env_default ADMIN_BOT_TOKEN)"
DEFAULT_ADMIN_ID="$(read_env_default ADMIN_ID)"
DEFAULT_APP_PIN="$(read_env_default APP_PIN)"
DEFAULT_APP_NAME="$(read_env_default APP_NAME)"
DEFAULT_KEEPALIVE_MINUTES="$(read_env_default KEEPALIVE_MINUTES)"

BOT_TOKEN_VAL="${BOT_TOKEN:-}"
ADMIN_BOT_TOKEN_VAL="${ADMIN_BOT_TOKEN:-$DEFAULT_ADMIN_BOT_TOKEN}"
ADMIN_ID_VAL="${ADMIN_ID:-}"
APP_PIN_VAL="${APP_PIN:-}"
APP_NAME_VAL="${APP_NAME:-}"
KEEPALIVE_MINUTES_VAL="${KEEPALIVE_MINUTES:-${DEFAULT_KEEPALIVE_MINUTES:-25}}"

prompt_var BOT_TOKEN_VAL "BOT_TOKEN" "$DEFAULT_BOT_TOKEN" 1
prompt_var ADMIN_ID_VAL "ADMIN_ID" "$DEFAULT_ADMIN_ID" 0
prompt_var APP_PIN_VAL "APP_PIN" "$DEFAULT_APP_PIN" 1
prompt_var APP_NAME_VAL "APP_NAME" "$DEFAULT_APP_NAME" 0

verify_bot_token() {
	local label="$1"
	local token="$2"
	local expected_suffix="$3"
	python3 - "$label" "$token" "$expected_suffix" <<'PY'
import json, sys, urllib.error, urllib.request

label, token, expected_suffix = sys.argv[1], sys.argv[2], sys.argv[3]
tail = f"...{token[-6:]}" if len(token) > 6 else "(short)"

def call(method):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {"ok": False, "description": str(e)}
        return e.code, body
    except Exception as e:
        return -1, {"ok": False, "description": str(e)}

code, me = call("getMe")
if code != 200 or not me.get("ok"):
    desc = me.get("description", "unknown error")
    print(f"Error: {label} [{tail}] getMe failed (HTTP {code}: {desc})", file=sys.stderr)
    sys.exit(1)
uname = me.get("result", {}).get("username", "?")
wcode, wh = call("getWebhookInfo")
if wcode != 200 or not wh.get("ok"):
    desc = wh.get("description", "unknown error")
    print(f"Error: {label} (@{uname}) getWebhookInfo failed (HTTP {wcode}: {desc})", file=sys.stderr)
    sys.exit(1)
info = wh.get("result", {})
wurl = info.get("url", "")
pend = info.get("pending_update_count", 0)
werr = info.get("last_error_message", "")
if not wurl:
    print(f"Error: {label} (@{uname}) has an empty webhook URL (expected suffix /{expected_suffix})", file=sys.stderr)
    sys.exit(1)
if expected_suffix and not wurl.rstrip("/").endswith("/" + expected_suffix):
    print(f"Error: {label} (@{uname}) webhook URL does not end with /{expected_suffix}", file=sys.stderr)
    sys.exit(1)
short_url = ("..." + wurl[-36:]) if len(wurl) > 39 else wurl
print(f"  {label} [{tail}]: @{uname} LIVE | webhook={short_url} | pending={pend}")
if werr:
    print(f"  Warning: {label} last webhook error: {werr}", file=sys.stderr)
PY
}

if [[ "${SKIP_TOKEN_CHECK:-0}" != "1" ]]; then
	echo "==> Verifying Telegram bot tokens & webhooks (set SKIP_TOKEN_CHECK=1 to skip)..."
	verify_bot_token "BOT_TOKEN" "$BOT_TOKEN_VAL" "komobotv2"
	if [[ -n "$ADMIN_BOT_TOKEN_VAL" ]]; then
		verify_bot_token "ADMIN_BOT_TOKEN" "$ADMIN_BOT_TOKEN_VAL" "komobotv2_admin"
	fi
fi

echo "==> Generating Komobot_Controller.macro..."
python3 "$SCRIPT_DIR/generate_macro.py" \
	--bot-token "$BOT_TOKEN_VAL" \
	--admin-bot-token "$ADMIN_BOT_TOKEN_VAL" \
	--admin-id "$ADMIN_ID_VAL" \
	--app-pin "$APP_PIN_VAL" \
	--app-name "$APP_NAME_VAL" \
	--keepalive-minutes "$KEEPALIVE_MINUTES_VAL"

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

tap_ui_node() {
	local pattern="$1"
	local xml
	xml="$(adb shell "uiautomator dump --compressed /data/local/tmp/md_ui.xml >/dev/null && cat /data/local/tmp/md_ui.xml" 2>/dev/null || true)"
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
    if rid == "android:id/aerr_wait":
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
        if m and pat != "android:id/aerr_wait":
            x1, y1, x2, y2 = map(int, m.groups())
            print("ANR_WAIT", (x1 + x2) // 2, (y1 + y2) // 2)
            sys.exit(0)
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
	if [[ "$coords" == ANR_WAIT* ]]; then
		set -- $coords
		adb shell input tap "$2" "$3"
		sleep 1
		return 1
	elif [[ -n "$coords" ]]; then
		adb shell input tap $coords
		return 0
	fi
	return 1
}

echo "==> Configuring MacroDroid Helper APK (per-request pocket/palm toggle)..."
setup_macrodroid_helper() {
	local helper_pkg="com.arlosoft.macrodroid.helper"
	local helper_url="https://macrodroidlink.com/helper/MacroDroidHelper.apk"
	local helper_apk="${MACRODROID_HELPER_APK:-/tmp/MacroDroidHelper.apk}"

	if ! adb shell pm path "$helper_pkg" >/dev/null 2>&1; then
		if [[ "${SKIP_HELPER_INSTALL:-0}" == "1" ]]; then
			echo "  $helper_pkg not installed (SKIP_HELPER_INSTALL=1)"
		else
			if [[ ! -f "$helper_apk" ]]; then
				echo "  fetching official MacroDroid Helper APK ($helper_url)..."
				if ! curl -fsSL "$helper_url" -o "$helper_apk"; then
					rm -f "$helper_apk"
					echo "  Warning: failed to download MacroDroid Helper APK." >&2
				fi
			fi
			if [[ -f "$helper_apk" ]]; then
				echo "  installing $helper_pkg with --bypass-low-target-sdk-block..."
				if adb install -r --bypass-low-target-sdk-block "$helper_apk"; then
					echo "  installed $helper_pkg"
				else
					echo "  Warning: failed to install $helper_pkg (if Play Protect blocked it, temporarily disable Developer options -> Verify apps over USB and re-run)." >&2
				fi
			fi
		fi
	else
		echo "  $helper_pkg already installed"
	fi

	if adb shell pm path "$helper_pkg" >/dev/null 2>&1; then
		for perm in \
			android.permission.WRITE_SECURE_SETTINGS \
			android.permission.WRITE_GLOBAL_SETTINGS; do
			adb shell pm grant "$helper_pkg" "$perm" 2>/dev/null || true
		done
		adb shell appops set "$helper_pkg" WRITE_SETTINGS allow 2>/dev/null || true
		adb shell dumpsys deviceidle whitelist "+$helper_pkg" >/dev/null 2>&1 || true
		for op in RUN_IN_BACKGROUND RUN_ANY_IN_BACKGROUND WAKE_LOCK; do
			adb shell appops set "$helper_pkg" "$op" allow 2>/dev/null || true
		done
		# Low-targetSdk (21) apps require a one-time permission review and launch before
		# Android's BroadcastQueue will deliver SystemSettingAction helper broadcasts.
		if adb shell "dumpsys package $helper_pkg | grep -qE 'REVIEW_REQUIRED|stopped=true'"; then
			echo "  completing one-time permission review & launch for $helper_pkg..."
			adb shell "input keyevent 224; wm dismiss-keyguard 2>/dev/null || true; sleep 0.4; am start -n $helper_pkg/.ui.HomeScreenActivity" >/dev/null 2>&1 || true
			sleep 1.5
			if tap_ui_node "com.android.permissioncontroller:id/continue_button"; then
				echo "  confirmed legacy permission review (Continue)"
				sleep 1.5
			fi
			if adb shell "dumpsys package $helper_pkg | grep -q 'stopped=true'"; then
				adb shell "am start -n $helper_pkg/.ui.HomeScreenActivity" >/dev/null 2>&1 || true
				sleep 1.2
			fi
		fi
		# Keep Samsung pocket/palm protection ON while idle; Stage 3/6 toggle them 0 -> 1 per request.
		adb shell settings put system screen_off_pocket 1 2>/dev/null || true
		adb shell settings put system surface_palm_touch 1 2>/dev/null || true
		echo "  configured $helper_pkg permissions & restored idle pocket/palm guards (1)"
	else
		echo "  Warning: $helper_pkg is not installed; per-request screen_off_pocket/surface_palm_touch toggles will not work." >&2
		echo "  Install manually: curl -fsSL $helper_url -o /tmp/MacroDroidHelper.apk && adb install -r --bypass-low-target-sdk-block /tmp/MacroDroidHelper.apk" >&2
	fi
}
setup_macrodroid_helper

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
adb shell settings put global wifi_suspend_optimizations_enabled 0 2>/dev/null || true
adb shell settings put system screen_off_timeout 120000 2>/dev/null || true
adb shell locksettings set-disabled true 2>/dev/null || true
adb shell settings put secure lockscreen.disabled 1 2>/dev/null || true
adb shell settings put secure lock_screen_lock_after_timeout 86400000 2>/dev/null || true

adb shell settings put system enable_smart_capture 0 2>/dev/null || true
adb shell settings put global window_animation_scale 0 2>/dev/null || true
adb shell settings put global transition_animation_scale 0 2>/dev/null || true
adb shell settings put global animator_duration_scale 0 2>/dev/null || true
adb shell cmd uimode night yes >/dev/null 2>&1 || true
adb shell settings put secure ui_night_mode 2 2>/dev/null || true
adb shell settings put system display_night_theme_scheduled 0 2>/dev/null || true
adb shell settings put system display_night_theme 1 2>/dev/null || true

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

accepted=0
for _ in 1 2 3 4 5 6 7 8; do
	sleep 1.5
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

for _ in 1 2 3 4 5 6; do
	sleep 1
	if tap_ui_node "OVERWRITE"; then
		echo "  Confirmed OVERWRITE existing macro"
		sleep 1.5
		break
	elif tap_ui_node "Import Macro"; then
		echo "  Import Macro dialog detected, tapping OVERWRITE fallback (537, 868)"
		adb shell input tap 537 868
		sleep 1.5
		break
	elif tap_ui_node "com.arlosoft.macrodroid:id/acceptButton"; then
		echo "  Re-tapped Add Macro (acceptButton)"
	fi
done

# MacroDroid sometimes imports the macro in the disabled state (e.g. after an ANR while
# a webhook push arrives). A disabled macro silently drops every webhook, so verify it.
macro_switch_state() {
	local xml
	xml="$(adb shell "uiautomator dump --compressed /data/local/tmp/md_ui.xml >/dev/null && cat /data/local/tmp/md_ui.xml" 2>/dev/null || true)"
	python3 -c '
import re, sys, xml.etree.ElementTree as ET
xml_str = sys.stdin.read()
idx = xml_str.find("<hierarchy")
if idx < 0:
    print("none")
    sys.exit(0)
root = ET.fromstring(xml_str[idx:])
has_nav = False
for node in root.iter("node"):
    if node.attrib.get("resource-id", "") == "com.arlosoft.macrodroid:id/navigation_macro_list":
        has_nav = True
for rid_target in ("com.arlosoft.macrodroid:id/enabledSwitch", "com.arlosoft.macrodroid:id/group_on_off_button"):
    for node in root.iter("node"):
        if has_nav and node.attrib.get("resource-id", "") == rid_target:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                print(node.attrib.get("checked", "false"), (x1 + x2) // 2, (y1 + y2) // 2)
                sys.exit(0)
print("none")
' <<<"$xml" 2>/dev/null || echo none
}

echo "==> Verifying the macro is enabled in MacroDroid..."
macro_enabled=0
adb shell monkey -p com.arlosoft.macrodroid -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 1.5
for _ in 1 2 3 4 5 6 7 8; do
	state="$(macro_switch_state)"
	set -- $state
	if [[ "${1:-none}" == "true" ]]; then
		macro_enabled=1
		echo "  Komobot Controller is enabled"
		break
	elif [[ "${1:-none}" == "false" ]]; then
		echo "  Macro is disabled, switching it on..."
		adb shell input tap "$2" "$3"
		sleep 1.5
	else
		tap_ui_node "com.arlosoft.macrodroid:id/navigation_macro_list" || true
		sleep 1.5
	fi
done
if [[ "$macro_enabled" -eq 0 ]]; then
	echo "Error: could not confirm that Komobot Controller is enabled; enable it manually in MacroDroid." >&2
	exit 1
fi

# Optional: the Virtual Master guest ships an emulated fingerprint HAL that spins one CPU
# core at ~100% from guest boot onwards. If the guest's adbd is reachable (guest USB
# debugging enabled and this PC authorized, listening on host localhost:GUEST_ADB_PORT),
# stop it. It returns after a guest reboot, so this only helps for the current boot.
# Skip with SKIP_GUEST_TWEAKS=1.
stop_guest_fps_hal() {
	[[ "${SKIP_GUEST_TWEAKS:-0}" == "1" ]] && return 0
	local host_serial guest_port local_port guest out
	host_serial="$(adb get-serialno 2>/dev/null | tr -d '\r' || true)"
	[[ -n "$host_serial" && "$host_serial" != "unknown" ]] || return 0
	guest_port="${GUEST_ADB_PORT:-10001}"
	local_port=15001
	guest="127.0.0.1:${local_port}"
	echo "==> Optional: stopping the runaway guest fingerprint HAL (set SKIP_GUEST_TWEAKS=1 to skip)..."
	if adb -s "$host_serial" forward "tcp:${local_port}" "tcp:${guest_port}" >/dev/null 2>&1; then
		timeout 10 adb connect "$guest" >/dev/null 2>&1 || true
		out="$(timeout 20 adb -s "$guest" shell '
state=$(getprop init.svc.vendor.fps_hal)
if [ "$state" = running ]; then
  setprop ctl.stop vendor.fps_hal
  sleep 0.5
  echo "state:$(getprop init.svc.vendor.fps_hal)"
else
  echo "idle:${state:-missing}"
fi' 2>/dev/null | tr -d '\r' || true)"
		case "$out" in
		"state:running" | "state:stopping") echo "  fps_hal is still active (${out#state:})" ;;
		state:stopped) echo "  guest fps_hal stopped" ;;
		idle:*) echo "  guest fps_hal already not running (${out#idle:}), nothing to do" ;;
		*) echo "  guest ADB not reachable/authorized, skipping" ;;
		esac
		if [[ "$out" == state:* || "$out" == idle:* ]]; then
			if ! timeout 10 adb -s "$guest" shell '[ -f /data/local/tmp/u2.jar ]' >/dev/null 2>&1; then
				if [[ ! -f /tmp/u2.jar ]]; then
					echo "  fetching u2.jar (uiautomator2==3.7.0)..."
					python3 -c '
import io, json, urllib.request, zipfile
meta = json.loads(urllib.request.urlopen("https://pypi.org/pypi/uiautomator2/3.7.0/json", timeout=15).read())
whl_url = next(u["url"] for u in meta["urls"] if u["packagetype"] == "bdist_wheel")
raw = urllib.request.urlopen(whl_url, timeout=30).read()
with zipfile.ZipFile(io.BytesIO(raw)) as zf:
    jar_name = next(n for n in zf.namelist() if n.endswith("u2.jar"))
    open("/tmp/u2.jar", "wb").write(zf.read(jar_name))
' >/dev/null 2>&1 || true
				fi
				if [[ -f /tmp/u2.jar ]]; then
					echo "  pushing u2.jar to guest /data/local/tmp/u2.jar..."
					timeout 20 adb -s "$guest" push /tmp/u2.jar /data/local/tmp/u2.jar >/dev/null 2>&1 || true
				fi
			fi
			timeout 15 adb -s "$guest" shell '
settings put global window_animation_scale 0
settings put global transition_animation_scale 0
settings put global animator_duration_scale 0
settings put system screen_off_timeout 2147483647
if [ -f /data/local/tmp/u2.jar ]; then
  if ! (printf "GET /ping HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n" | nc -w 1 127.0.0.1 9008 | grep -q pong); then
    nohup sh -c "CLASSPATH=/data/local/tmp/u2.jar app_process / com.wetest.uia2.Main -p 9008" >/data/local/tmp/u2.log 2>&1 </dev/null &
  fi
fi' >/dev/null 2>&1 || true
			echo "  guest VM animations disabled & u2.jar server checked"
		fi
		timeout 10 adb disconnect "$guest" >/dev/null 2>&1 || true
		adb -s "$host_serial" forward --remove "tcp:${local_port}" >/dev/null 2>&1 || true
	else
		echo "  could not forward the guest ADB port, skipping"
	fi
}
stop_guest_fps_hal || true

# Leave MacroDroid's UI: if its activity stays foreground while a webhook run starts, the
# focus/screen-on churn can trigger "MacroDroid isn't responding" and that dialog eats taps.
echo "==> Returning to Home and clearing any ANR dialog..."
for _ in 1 2 3; do
	anr_xy="$(adb shell "uiautomator dump --compressed /data/local/tmp/md_anr.xml >/dev/null 2>&1 && cat /data/local/tmp/md_anr.xml" 2>/dev/null | tr -d '\r' | python3 -c '
import re, sys
xml = sys.stdin.read()
m = re.search(r"resource-id=\"android:id/aerr_wait\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"", xml)
if m:
    x1, y1, x2, y2 = map(int, m.groups())
    print((x1 + x2) // 2, (y1 + y2) // 2)
' 2>/dev/null || true)"
	[[ -z "$anr_xy" ]] && break
	echo "  ANR dialog found, tapping Wait"
	adb shell input tap $anr_xy
	sleep 1
done
adb shell "input keyevent KEYCODE_HOME" || true

sleep 1
adb shell rm -f /storage/emulated/0/Download/Komobot_Controller.macro /data/local/tmp/md_ui.xml
echo "==> Done deploying Komobot_Controller.macro to MacroDroid."
