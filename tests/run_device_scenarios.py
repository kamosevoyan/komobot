#!/usr/bin/env python3
"""Hardware-in-the-loop end-to-end scenario runner for Komobot over ADB & webhooks.

Safety guarantees:
  * Never touches Telcell Wallet login state or sends input taps inside VM/Telcell.
  * Synthetic webhook requests use ``"update_id": 0`` (except ``dedup``, which sends
    the existing ``last_update_id``) so Telegram's real update counter is untouched.
  * Never sends messages to third-party chats (only ``ADMIN_ID`` or ``-999999999``).

Note: Scenarios that target ``ADMIN_ID`` send real progress/QR messages to the admin
Telegram chat and wake the connected Android device.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
CONFIG_DEVICE_PATH = "/storage/emulated/0/Download/komobot_config.json"


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def adb(*args: str) -> str:
    res = subprocess.run(
        ["adb", *args], check=True, capture_output=True, text=True, timeout=15
    )
    return res.stdout.strip()


def read_device_config() -> dict:
    raw = adb("shell", "cat", CONFIG_DEVICE_PATH)
    return json.loads(raw)


def get_wakefulness() -> str:
    out = adb("shell", "dumpsys power | grep mWakefulness=")
    m = re.search(r"mWakefulness=(\S+)", out)
    return m.group(1) if m else "Unknown"


def ensure_dozing(wait_s: float = 12.0) -> None:
    last_sleep_cmd = 0.0
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if get_wakefulness() == "Dozing":
            return
        now = time.monotonic()
        if now - last_sleep_cmd >= 3.0:
            adb("shell", "input", "keyevent", "223")
            last_sleep_cmd = now
        time.sleep(1.0)
    raise AssertionError(f"Device did not enter Dozing (state={get_wakefulness()})")


def resolve_webhook_url(bot_token: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    env_url = os.environ.get("WEBHOOK_URL", "").strip()
    if env_url:
        return env_url
    req = urllib.request.urlopen(
        f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=10
    )
    info = json.loads(req.read().decode("utf-8"))
    url = info.get("result", {}).get("url", "")
    if not url:
        raise RuntimeError(
            "Telegram getWebhookInfo returned an empty URL; pass --webhook-url."
        )
    return url


def redact_webhook_url(url: str) -> str:
    return re.sub(r"(/[0-9a-fA-F-]{8,}/)", "/<redacted>/", url)


def post_webhook(url: str, *, update_id: int, chat_id: int, text: str) -> int:
    payload = json.dumps(
        {
            "update_id": update_id,
            "message": {"message_id": 99999, "chat": {"id": chat_id}, "text": text},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def wait_until_idle(*, previous_run_start: int, timeout_s: float) -> tuple[dict, float]:
    start = time.monotonic()
    deadline = start + timeout_s
    saw_run = False
    latest_cfg: dict = {}
    while time.monotonic() < deadline:
        latest_cfg = read_device_config()
        run_started = latest_cfg.get("run_start_ms", 0) != previous_run_start
        busy_until = latest_cfg.get("busy_until", 0)
        if run_started or busy_until > 0:
            saw_run = True
        if saw_run and busy_until == 0 and get_wakefulness() == "Dozing":
            return latest_cfg, time.monotonic() - start
        time.sleep(1.5)
    raise AssertionError(
        f"Timed out after {timeout_s:.1f}s (wake={get_wakefulness()}, "
        f"state={latest_cfg.get('last_state')}, step={latest_cfg.get('step_count')}, "
        f"busy_until={latest_cfg.get('busy_until')})"
    )


@dataclass(frozen=True)
class ScenarioContext:
    webhook_url: str
    admin_id: int
    timeout_s: float
    idle_wait_s: float = 8.0


def scenario_dedup(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    uid = int(before.get("last_update_id", 0))
    if uid <= 0:
        return "SKIPPED (last_update_id == 0 on device)"
    post_webhook(
        ctx.webhook_url,
        update_id=uid,
        chat_id=ctx.admin_id,
        text="__komobot_dedup_probe__",
    )
    time.sleep(2.5)
    after = read_device_config()
    assert after.get("last_msg_text") == before.get("last_msg_text"), after
    assert after.get("busy_until", 0) == 0, after
    assert get_wakefulness() == "Dozing"
    return f"ignored duplicate update_id={uid}"


def scenario_unauthorized(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    fake_cid = -999999999
    post_webhook(
        ctx.webhook_url, update_id=0, chat_id=fake_cid, text="📸 Take QR Screenshot"
    )
    deadline = time.monotonic() + 10.0
    after = before
    while time.monotonic() < deadline:
        after = read_device_config()
        if after.get("last_chat_id") == fake_cid:
            break
        time.sleep(1.0)
    assert after.get("last_chat_id") == fake_cid, after
    assert after.get("busy_until", 0) == 0, after
    assert after.get("last_update_id") == before.get("last_update_id"), after
    assert get_wakefulness() == "Dozing"
    return "rejected fake chat_id without waking phone"


def scenario_toggle_restore(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    orig_pub = bool(before.get("public_access", True))

    def wait_pub(expected: bool) -> dict:
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            cur = read_device_config()
            if cur.get("public_access") is expected:
                return cur
            time.sleep(1.0)
        raise AssertionError(f"public_access did not transition to {expected}")

    post_webhook(
        ctx.webhook_url,
        update_id=0,
        chat_id=ctx.admin_id,
        text="🛑 Toggle Public Access",
    )
    wait_pub(not orig_pub)
    post_webhook(
        ctx.webhook_url,
        update_id=0,
        chat_id=ctx.admin_id,
        text="🛑 Toggle Public Access",
    )
    restored = wait_pub(orig_pub)
    assert restored.get("last_update_id") == before.get("last_update_id")
    assert get_wakefulness() == "Dozing"
    return f"toggled public_access {orig_pub} -> {not orig_pub} -> {orig_pub}"


def scenario_reset(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    post_webhook(
        ctx.webhook_url, update_id=0, chat_id=ctx.admin_id, text="🧹 Reset VM App"
    )
    cfg, elapsed = wait_until_idle(
        previous_run_start=before.get("run_start_ms", 0), timeout_s=ctx.timeout_s
    )
    assert cfg.get("last_state") == "RESET", cfg
    assert cfg.get("queue") == [], cfg
    assert cfg.get("last_update_id") == before.get("last_update_id"), cfg
    return f"last_state=RESET steps={cfg.get('step_count')} in {elapsed:.1f}s"


def scenario_qr(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    post_webhook(
        ctx.webhook_url, update_id=0, chat_id=ctx.admin_id, text="📸 Take QR Screenshot"
    )
    cfg, elapsed = wait_until_idle(
        previous_run_start=before.get("run_start_ms", 0), timeout_s=ctx.timeout_s
    )
    assert cfg.get("last_state") == "QR_SENT", cfg
    assert cfg.get("last_update_id") == before.get("last_update_id"), cfg
    assert cfg.get("last_ss_mtime", 0) >= before.get("last_ss_mtime", 0), cfg
    return (
        f"last_state=QR_SENT steps={cfg.get('step_count')} "
        f"other={cfg.get('other_count')} white={cfg.get('white_count')} "
        f"loading={cfg.get('loading_count')} in {elapsed:.1f}s"
    )


def scenario_duplicate_busy(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    prev_start = before.get("run_start_ms", 0)
    post_webhook(
        ctx.webhook_url, update_id=0, chat_id=ctx.admin_id, text="📸 Take QR Screenshot"
    )
    lease_deadline = time.monotonic() + 15.0
    while time.monotonic() < lease_deadline:
        cur = read_device_config()
        if cur.get("run_start_ms", 0) != prev_start and cur.get("busy_until", 0) > 0:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("First request did not claim active lease within 15s")
    time.sleep(3.5)
    post_webhook(
        ctx.webhook_url, update_id=0, chat_id=ctx.admin_id, text="📸 Take QR Screenshot"
    )
    cfg, elapsed = wait_until_idle(
        previous_run_start=prev_start, timeout_s=ctx.timeout_s
    )
    assert cfg.get("last_state") == "QR_SENT", cfg
    assert cfg.get("queue") == [], cfg
    assert cfg.get("last_update_id") == before.get("last_update_id"), cfg
    return (
        f"duplicate rejected while busy; completed QR_SENT in {elapsed:.1f}s "
        f"(steps={cfg.get('step_count')})"
    )


def scenario_inactivity_audit(ctx: ScenarioContext) -> str:
    del ctx
    whitelist = adb("shell", "dumpsys", "deviceidle", "whitelist")
    for pkg in ("com.arlosoft.macrodroid", "com.clone.android.dual.space"):
        assert pkg in whitelist, f"{pkg} missing from deviceidle whitelist"

    macro_bucket = int(
        adb("shell", "am", "get-standby-bucket", "com.arlosoft.macrodroid")
    )
    vm_bucket = int(
        adb("shell", "am", "get-standby-bucket", "com.clone.android.dual.space")
    )
    assert macro_bucket <= 10, (
        f"MacroDroid standby bucket too restricted: {macro_bucket}"
    )
    assert vm_bucket <= 10, f"Virtual Master standby bucket too restricted: {vm_bucket}"

    deviceidle_dump = adb("shell", "dumpsys", "deviceidle")
    assert "mLightEnabled=false" in deviceidle_dump, "Light Doze is still enabled"
    assert "mDeepEnabled=false" in deviceidle_dump, "Deep Doze is still enabled"

    app_standby = adb("shell", "settings", "get", "global", "app_standby_enabled")
    assert app_standby == "0", f"app_standby_enabled={app_standby!r}"

    phantom_mon = adb(
        "shell", "settings", "get", "global", "settings_enable_monitor_phantom_procs"
    )
    assert phantom_mon == "false", (
        f"settings_enable_monitor_phantom_procs={phantom_mon!r}"
    )

    max_procs = adb(
        "shell",
        "cmd",
        "device_config",
        "get",
        "activity_manager",
        "max_phantom_processes",
    )
    assert int(max_procs) >= 2147483647, f"max_phantom_processes={max_procs!r}"

    wifi_sleep = adb("shell", "settings", "get", "global", "wifi_sleep_policy")
    assert wifi_sleep == "2", f"wifi_sleep_policy={wifi_sleep!r}"

    wifi_ps = adb("shell", "settings", "get", "global", "wifi_power_save")
    assert wifi_ps == "0", f"wifi_power_save={wifi_ps!r}"

    lock_disabled = adb("shell", "settings", "get", "secure", "lockscreen.disabled")
    assert lock_disabled == "1", f"lockscreen.disabled={lock_disabled!r}"

    acc = adb("shell", "settings", "get", "secure", "enabled_accessibility_services")
    assert "com.arlosoft.macrodroid" in acc, f"MacroDroid Accessibility off: {acc!r}"

    for op in (
        "WAKE_LOCK",
        "SYSTEM_ALERT_WINDOW",
        "RUN_ANY_IN_BACKGROUND",
        "MANAGE_EXTERNAL_STORAGE",
    ):
        out = adb("shell", "appops", "get", "com.arlosoft.macrodroid", op)
        assert "allow" in out, f"MacroDroid appop {op} not allowed: {out!r}"

    for scale in (
        "window_animation_scale",
        "transition_animation_scale",
        "animator_duration_scale",
    ):
        val = adb("shell", "settings", "get", "global", scale)
        assert val in ("0", "0.0"), f"{scale}={val!r} (expected 0)"

    nomedia = adb(
        "shell", "test -f /storage/emulated/0/komobot_ss/.nomedia && echo ok"
    )
    assert nomedia == "ok", "Missing /storage/emulated/0/komobot_ss/.nomedia"

    night_mode = adb("shell", "cmd uimode night")
    assert "yes" in night_mode.lower(), f"Expected locked Dark Mode: {night_mode!r}"

    return (
        f"buckets=({macro_bucket},{vm_bucket}) doze=off anim=0 night=yes "
        f"phantom_mon={phantom_mon} max_procs={max_procs} "
        f"wifi_sleep={wifi_sleep} lock_disabled={lock_disabled}"
    )


def scenario_unplugged_doze_qr(ctx: ScenarioContext) -> str:
    ensure_dozing()
    before = read_device_config()
    try:
        adb("shell", "dumpsys", "battery", "unplug")
        time.sleep(1.0)
        ensure_dozing()
        time.sleep(ctx.idle_wait_s)
        post_webhook(
            ctx.webhook_url,
            update_id=0,
            chat_id=ctx.admin_id,
            text="📸 Take QR Screenshot",
        )
        cfg, elapsed = wait_until_idle(
            previous_run_start=before.get("run_start_ms", 0), timeout_s=ctx.timeout_s
        )
    finally:
        adb("shell", "dumpsys", "battery", "reset")
    assert cfg.get("last_state") == "QR_SENT", cfg
    assert cfg.get("last_update_id") == before.get("last_update_id"), cfg
    assert get_wakefulness() == "Dozing"
    return (
        f"unplugged idle={ctx.idle_wait_s:.1f}s -> QR_SENT "
        f"steps={cfg.get('step_count')} in {elapsed:.1f}s"
    )


SCENARIOS: dict[str, tuple[str, Callable[[ScenarioContext], str]]] = {
    "inactivity_audit": (
        "Audit Doze, standby, Phantom Process Killer, Wi-Fi & lockscreen flags",
        scenario_inactivity_audit,
    ),
    "dedup": ("Verify repeated last_update_id is ignored safely", scenario_dedup),
    "unauthorized": (
        "Verify unknown chat_id is rejected without waking screen",
        scenario_unauthorized,
    ),
    "toggle_restore": (
        "Verify admin public_access toggle flips and restores cleanly",
        scenario_toggle_restore,
    ),
    "reset": ("Verify admin Reset VM App clears state and sleeps", scenario_reset),
    "qr": (
        "Verify full Doze wake -> VM/Telcell -> QR_SENT -> Dozing cycle",
        scenario_qr,
    ),
    "duplicate_busy": (
        "Verify second request from active user while busy does not disrupt QR_SENT",
        scenario_duplicate_busy,
    ),
    "unplugged_doze_qr": (
        "Verify QR delivery after idling screen-off with simulated battery unplug",
        scenario_unplugged_doze_qr,
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run live Komobot webhook scenarios against a connected phone."
    )
    parser.add_argument(
        "--scenario",
        nargs="+",
        default=[
            "inactivity_audit",
            "dedup",
            "unauthorized",
            "toggle_restore",
            "reset",
            "qr",
        ],
        help="Scenario names to run, or 'all' (default: audit + non-busy suite).",
    )
    parser.add_argument("--list", action="store_true", help="List available scenarios.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify ADB device, config, and webhook URL without sending webhooks.",
    )
    parser.add_argument("--webhook-url", default=None, help="Override MacroDroid URL.")
    parser.add_argument(
        "--timeout", type=float, default=75.0, help="Per-run wait timeout in seconds."
    )
    parser.add_argument(
        "--idle-wait",
        type=float,
        default=8.0,
        help="Seconds to stay unplugged in Dozing during unplugged_doze_qr.",
    )
    args = parser.parse_args()

    if args.list:
        for name, (desc, _) in SCENARIOS.items():
            print(f"  {name:16s} {desc}")
        return 0

    selected = list(SCENARIOS) if "all" in args.scenario else args.scenario
    unknown = [s for s in selected if s not in SCENARIOS]
    if unknown:
        print(f"Unknown scenario(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    env_vals = load_dotenv(ENV_PATH)
    bot_token = os.environ.get("BOT_TOKEN", env_vals.get("BOT_TOKEN", ""))
    admin_str = os.environ.get("ADMIN_ID", env_vals.get("ADMIN_ID", ""))
    if not admin_str or (not args.webhook_url and not bot_token):
        print(
            "BOT_TOKEN and ADMIN_ID must be set in .env or environment.",
            file=sys.stderr,
        )
        return 2
    admin_id = int(admin_str)

    try:
        state = adb("get-state")
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"ADB device not ready: {err}", file=sys.stderr)
        return 1
    if state != "device":
        print(f"ADB device not ready (state={state})", file=sys.stderr)
        return 1
    cfg = read_device_config()
    webhook_url = resolve_webhook_url(bot_token, args.webhook_url)

    print(
        f"Device ready | wakefulness={get_wakefulness()} "
        f"| last_state={cfg.get('last_state')}"
    )
    print(f"Webhook: {redact_webhook_url(webhook_url)}")
    print(f"Scenarios: {', '.join(selected)}")
    if args.dry_run:
        print("Dry run complete.")
        return 0

    ctx = ScenarioContext(
        webhook_url=webhook_url,
        admin_id=admin_id,
        timeout_s=args.timeout,
        idle_wait_s=args.idle_wait,
    )
    failures = 0
    for name in selected:
        _, fn = SCENARIOS[name]
        print(f"[RUN ] {name} ...", flush=True)
        try:
            detail = fn(ctx)
            print(f"[PASS] {name}: {detail}")
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
