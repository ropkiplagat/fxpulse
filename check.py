"""
FXPulse Diagnostic — run with: C:\Python310\python.exe check.py
Checks imports, .env, logs, and bot state.
"""
import os, sys, json
from datetime import datetime, timezone

BOT_DIR = r"C:\fxpulse"
sys.path.insert(0, BOT_DIR)
os.chdir(BOT_DIR)

print("=" * 50)
print("FXPulse Diagnostic")
print("=" * 50)

# 1. Check imports
modules = ["config", "siteground_api", "copy_trades"]
for m in modules:
    try:
        __import__(m)
        print(f"[OK] import {m}")
    except Exception as e:
        print(f"[FAIL] import {m}: {e}")

# 2. Check .env
print()
env_file = os.path.join(BOT_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        keys = [line.split("=")[0].strip() for line in f if "=" in line and not line.startswith("#")]
    print(f"[OK] .env found — keys: {', '.join(keys)}")
else:
    print("[FAIL] .env missing")

# 3. Check GITHUB_TOKEN
try:
    import config
    tok = getattr(config, "GITHUB_TOKEN", "")
    print(f"[OK] GITHUB_TOKEN: {tok[:10]}..." if tok else "[FAIL] GITHUB_TOKEN empty")
except:
    print("[FAIL] Could not load config")

# 4. Last 20 lines of service.log
print()
log = os.path.join(BOT_DIR, "logs", "service.log")
if os.path.exists(log):
    with open(log) as f:
        lines = f.readlines()
    print(f"--- Last 20 lines of service.log ---")
    print("".join(lines[-20:]))
else:
    print("[WARN] service.log not found")

# 5. Bot state age
state_file = os.path.join(BOT_DIR, "logs", "bot_state.json")
if os.path.exists(state_file):
    try:
        with open(state_file) as f:
            state = json.load(f)
        updated = state.get("updated", "")
        if updated:
            dt  = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds() / 60
            print(f"[OK] bot_state.json age: {age:.1f} min")
        else:
            print("[WARN] bot_state.json has no updated field")
    except Exception as e:
        print(f"[FAIL] bot_state.json error: {e}")
else:
    print("[WARN] bot_state.json not found")

print("=" * 50)
