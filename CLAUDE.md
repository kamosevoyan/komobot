# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Komobot generates a **MacroDroid macro** (JSON) that turns an Android phone into a Telegram QR-code responder for Telcell Wallet running inside Virtual Master. There is no runtime server: the Python here is only a *generator* plus tests. All runtime logic lives in BeanShell (`JavaAction`) scripts embedded as strings inside `generate_macro.py`. `README.md` has the full pipeline diagram, stage descriptions and screen-state coordinates — read it before changing behavior.

## Commands

```bash
# Generate Komobot_Controller.macro (gitignored output) — args default to empty
python3 generate_macro.py --bot-token X --admin-id Y --app-pin Z --app-name PKG

# Generate + push to phone over ADB (reads defaults from .env: BOT_TOKEN, ADMIN_ID, APP_PIN, APP_NAME; also applies Doze/animation/night-mode device settings)
./deploy_macro.sh

# Offline tests (no phone). Run from repo root; tests import generate_macro directly where needed
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_vision_scenarios -v            # one file
python3 -m unittest tests.test_vision_scenarios.<Class>.<test> # one test

# Hardware-in-the-loop scenarios (needs ADB phone + real bot; sends real Telegram messages)
python3 tests/run_device_scenarios.py --list
python3 tests/run_device_scenarios.py --dry-run

# Lint/format (dev deps via uv: ruff, shfmt-py)
uv run ruff check . && uv run ruff format .
```

Ruff: line length 88, rules `E`,`I`; `generate_macro.py` has `# ruff: noqa: E501` because of embedded script strings.

## Architecture

- `generate_macro.py` has two layers: (1) `make_*` helpers that build MacroDroid action/constraint dicts with deterministic negative `SiguidGen` IDs (keep generator output deterministic); (2) `build_*_script()` functions returning the five BeanShell scripts — `router` (auth/queue/lease), `init_status`, `vision` (pixel classifier that emits `step_cmd`), `post_step`, `timeout` — which `build_macro()` wires into the 5-stage macro with a 130× loop in Stage 4.
- Runtime state is a single JSON file on the phone (`komobot_config.json`: users, queue, `busy_until` lease, worker heartbeat, etc.), mutated by the scripts. Router and vision scripts coordinate via that config and local macro variables (`step_cmd`, `mode`, …).
- Screen coordinates are calibrated for 720x1600 (scaled for other resolutions in vision tests); changing UI taps/PIN coords means updating both generator and tests.

## Test harness

`tests/bsh_runtime.py` is a custom mini BeanShell/Java-subset compiler (translates to Python) with mocked Android Bitmap, filesystem, clock and Telegram HTTP. Tests extract the *actual* generated scripts and run them in it, so new Java constructs/APIs used in the generated scripts may require extending this runtime. BeanShell strings must not contain raw newlines (guarded by `test_macro_structure.py`). Test files: structure, router/timeout scenarios, and vision scenarios.
