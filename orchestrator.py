"""
orchestrator.py — FXPulse DOE Framework: ORCHESTRATOR
======================================================
Replaces watchdog.bat as the main entry point.

What it does:
- Runs main.py as a subprocess (the Executor agent)
- Captures ALL output to agent_output.log
- On crash: logs error + last 50 lines → sends SMS alert → waits → restarts
- Fast crash detection: if uptime < 10s it's a code error → longer backoff
- After 5 fast crashes: CRITICAL alert → 5 min wait
- After 20 total restarts: give up + alert for manual fix
- Writes heartbeat every 60s so health_monitor knows it's alive

Run via Scheduled Task: C:\Python310\python.exe orchestrator.py
WorkingDir: C:\fxpulse
"""

import os
import sys
import time
import subprocess
import threading
import json
from datetime import datetime, timezone

# ── Bootstrap ─────────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

import director as D

os.makedirs(D.LOG_DIR, exist_ok=True)


# ── Logger ────────────────────────────────────────────────────────────────────
def _log(msg: str):
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(D.ORCH_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Keep log under 2000 lines
        with open(D.ORCH_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 2000:
            with open(D.ORCH_LOG, "w", encoding="utf-8") as f:
                f.writelines(lines[-1500:])
    except Exception:
        pass


# ── SMS Alert (reads Twilio from .env) ────────────────────────────────────────
def _load_env() -> dict:
    env  = {}
    path = os.path.join(D.BOT_DIR, ".env")
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _send_sms(body: str):
    try:
        import urllib.request, urllib.parse, base64
        env   = _load_env()
        sid   = env.get("TWILIO_SID",   "")
        token = env.get("TWILIO_TOKEN", "")
        from_ = env.get("TWILIO_FROM",  "")
        if not sid or not token or not from_:
            _log("[SMS] Twilio creds missing — skipping SMS")
            return
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = urllib.parse.urlencode({"To": D.ALERT_PHONE, "From": from_, "Body": body}).encode()
        req  = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 201:
                _log(f"[SMS] Sent: {body[:60]}")
    except Exception as e:
        _log(f"[SMS] Failed: {e}")


def _send_telegram(body: str):
    try:
        import urllib.request
        env   = _load_env()
        token = env.get("TELEGRAM_TOKEN", "")
        chat  = env.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat:
            return
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat, "text": body, "parse_mode": "Markdown"}).encode()
        req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        _log(f"[TG] Sent: {body[:60]}")
    except Exception as e:
        _log(f"[TG] Failed: {e}")


def _alert(body: str):
    """Send via Telegram first, fall back to SMS."""
    _send_telegram(body)
    _send_sms(body)


# ── Tail log file ─────────────────────────────────────────────────────────────
def _tail(path: str, n: int = 50) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception:
        return "(no log)"


# ── Heartbeat writer ──────────────────────────────────────────────────────────
_hb_stop = threading.Event()

def _heartbeat_worker():
    hb_file = os.path.join(D.LOG_DIR, "orchestrator_heartbeat.txt")
    while not _hb_stop.is_set():
        try:
            with open(hb_file, "w") as f:
                f.write(datetime.now(timezone.utc).isoformat())
        except Exception:
            pass
        _hb_stop.wait(60)

threading.Thread(target=_heartbeat_worker, daemon=True, name="Heartbeat").start()


# ── Main Orchestrator Loop ────────────────────────────────────────────────────
def run():
    total_restarts = 0
    fast_crashes   = 0
    last_fast_time = 0.0

    _log("=" * 60)
    _log("FXPulse Orchestrator starting")
    _log(f"  Python : {sys.executable}")
    _log(f"  Bot dir: {D.BOT_DIR}")
    _log(f"  Policy : max {D.MAX_TOTAL_RESTARTS} restarts, "
         f"{D.MAX_FAST_CRASHES} fast crashes → critical")
    _log("=" * 60)

    while True:
        if total_restarts >= D.MAX_TOTAL_RESTARTS:
            msg = (f"FXPulse CRITICAL: bot restarted {total_restarts} times "
                   f"and keeps crashing. Manual fix needed. "
                   f"RDP to {D.VPS_IP}")
            _log(f"[ORCH] {msg}")
            _alert(msg)
            _log("[ORCH] Giving up. Exiting orchestrator.")
            break

        _log(f"[ORCH] Launching main.py (attempt #{total_restarts + 1})")

        # Open agent log in append mode — captures all stdout+stderr
        agent_log_fh = open(D.AGENT_LOG, "a", encoding="utf-8", buffering=1)
        agent_log_fh.write(f"\n{'='*60}\n")
        agent_log_fh.write(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] "
                           f"LAUNCH attempt #{total_restarts + 1}\n")
        agent_log_fh.flush()

        start_time = time.time()
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=agent_log_fh,
            stderr=agent_log_fh,
            cwd=D.BOT_DIR,
        )

        exit_code = proc.wait()
        uptime    = time.time() - start_time
        agent_log_fh.close()

        total_restarts += 1
        _log(f"[ORCH] main.py exited — code={exit_code}, uptime={uptime:.1f}s")

        if exit_code == 0:
            _log("[ORCH] Clean exit (code 0) — not restarting.")
            break

        # ── Fast crash detection ──────────────────────────────────────────────
        is_fast = uptime < D.FAST_CRASH_SEC
        if is_fast:
            fast_crashes += 1
            last_fast_time = time.time()
            _log(f"[ORCH] Fast crash #{fast_crashes} (uptime {uptime:.1f}s < {D.FAST_CRASH_SEC}s)")
        else:
            # Reset fast crash counter if uptime was healthy
            if time.time() - last_fast_time > 300:
                fast_crashes = 0

        # ── Build alert message ───────────────────────────────────────────────
        tail = _tail(D.AGENT_LOG, 30)
        # Find last error line
        error_hint = ""
        for line in tail.splitlines()[::-1]:
            if "Error" in line or "error" in line or "Traceback" in line:
                error_hint = line.strip()[:120]
                break

        if fast_crashes >= D.MAX_FAST_CRASHES:
            wait  = D.CRITICAL_WAIT_SEC
            level = "CRITICAL"
            fast_crashes = 0  # Reset after critical alert
        else:
            wait  = D.RESTART_DELAY_SEC
            level = "WARNING"

        msg = (
            f"FXPulse {level}: bot crashed "
            f"(exit={exit_code}, uptime={uptime:.1f}s, restart #{total_restarts}). "
            f"{('Error: ' + error_hint) if error_hint else 'Check agent_output.log'} "
            f"— restarting in {wait}s."
        )
        _log(f"[ORCH] {msg}")
        _alert(msg)

        _log(f"[ORCH] Waiting {wait}s before restart...")
        time.sleep(wait)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        _log("[ORCH] Stopped by user.")
    finally:
        _hb_stop.set()
