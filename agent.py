"""
FXPulse Agent — Autonomous monitoring and self-healing daemon.
Runs every 2 minutes via FXPulse-Agent scheduled task.

CHECK 1: GitHub Push Health  — verify bot state is reaching GitHub
CHECK 2: Dashboard Health    — verify myforexpulse.com is reachable
CHECK 3: Bot Guardian        — ensure main.py is running; restart if stale
CHECK 4: Infra Guardian      — log rotation, disk space
CHECK 5: Reporter            — SMS on failures, daily 7am AEST summary
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE        = Path("C:/fxpulse")
LOGS        = BASE / "logs"
LOG_FILE    = LOGS / "agent.log"
STATE_FILE  = LOGS / "agent_state.json"
REPORT_FILE = LOGS / "agent_report.json"
BOT_STATE   = LOGS / "bot_state.json"
ERROR_LOG   = LOGS / "error.log"
PYTHON      = "C:/Python310/python.exe"
MAIN_PY     = str(BASE / "main.py")

LOGS.mkdir(parents=True, exist_ok=True)

MAX_RESTARTS        = 3
BOT_STALE_MINUTES   = 5
DISK_WARN_GB        = 1.0
LOG_ROTATE_MB       = 50
DAILY_REPORT_HOUR   = 7   # 7am AEST = UTC+10


# ── Env loader ───────────────────────────────────────────────────────────────
def _load_env():
    env_path = BASE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

TWILIO_SID   = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM  = os.environ.get("TWILIO_FROM", "")
TWILIO_TO    = os.environ.get("TWILIO_TO", "+61489263227")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = "ropkiplagat/fxpulse"


# ── Logging ──────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode('ascii', 'replace').decode())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── State persistence ────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "fix_attempts": 0,
        "consecutive_failures": 0,
        "last_fix": None,
        "last_alert": None,
        "last_daily_report": None,
        "total_fixes": 0,
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def append_report(entry: dict):
    history = []
    if REPORT_FILE.exists():
        try:
            history = json.loads(REPORT_FILE.read_text())
        except Exception:
            pass
    history.append(entry)
    history = history[-200:]  # keep last 200 entries
    REPORT_FILE.write_text(json.dumps(history, indent=2, default=str))


def tail_log(path: Path, lines: int = 5) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except Exception:
        return "Could not read log"


# ── SMS ──────────────────────────────────────────────────────────────────────
def send_sms(body: str):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
        log("[SMS] Twilio credentials missing — skipping SMS")
        return
    try:
        import base64
        payload = urllib.parse.urlencode({
            "To": TWILIO_TO, "From": TWILIO_FROM, "Body": body
        }).encode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Authorization": f"Basic {creds}"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            log(f"[SMS] Sent: {body[:60]}")
    except Exception as e:
        log(f"[SMS] Failed: {e}")

import urllib.parse


# ── CHECK 1: GitHub Push Health ──────────────────────────────────────────────
def check_github_push() -> bool:
    log("[CHECK1] GitHub push health...")
    if not GITHUB_TOKEN:
        log("[CHECK1] WARN: GITHUB_TOKEN missing")
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/commits?path=bot_state.json&per_page=1"
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "User-Agent": "fxpulse-agent"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            commits = json.loads(r.read())
        if not commits:
            log("[CHECK1] WARN: No bot_state.json commits found")
            return False
        last_commit_time = commits[0]["commit"]["committer"]["date"]
        dt = datetime.fromisoformat(last_commit_time.replace("Z", "+00:00"))
        age_min = (datetime.now(timezone.utc) - dt).total_seconds() / 60
        if age_min > 10:
            log(f"[CHECK1] WARN: Last GitHub push was {age_min:.0f} min ago")
            return False
        log(f"[CHECK1] OK — last push {age_min:.1f} min ago")
        return True
    except Exception as e:
        log(f"[CHECK1] ERROR: {e}")
        return False


# ── CHECK 2: Dashboard Health ────────────────────────────────────────────────
def check_dashboard() -> bool:
    log("[CHECK2] Dashboard health...")
    try:
        req = urllib.request.Request(
            "https://myforexpulse.com/dashboard.php",
            headers={"User-Agent": "fxpulse-agent"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
            status = r.getcode()
        if status == 200 and ("FXPulse" in body or "dashboard" in body.lower()):
            log(f"[CHECK2] OK — dashboard reachable (HTTP {status})")
            return True
        log(f"[CHECK2] WARN — unexpected response HTTP {status}")
        return False
    except Exception as e:
        log(f"[CHECK2] ERROR: {e}")
        return False


# ── CHECK 3: Bot Guardian ────────────────────────────────────────────────────
def is_bot_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True, text=True
        )
        return "python.exe" in result.stdout
    except Exception:
        return False


def is_bot_state_fresh() -> bool:
    if not BOT_STATE.exists():
        return False
    age = (datetime.now(timezone.utc) - datetime.fromtimestamp(
        BOT_STATE.stat().st_mtime, tz=timezone.utc
    )).total_seconds() / 60
    return age <= BOT_STALE_MINUTES


def kill_python():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
        time.sleep(3)
        log("[CHECK3] Killed python.exe")
    except Exception as e:
        log(f"[CHECK3] Kill failed: {e}")


def start_bot():
    try:
        subprocess.Popen(
            [PYTHON, MAIN_PY],
            cwd=str(BASE),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        log("[CHECK3] Bot started")
    except Exception as e:
        log(f"[CHECK3] Start failed: {e}")


def check_bot_guardian(state: dict) -> tuple[bool, dict]:
    log("[CHECK3] Bot guardian...")
    running = is_bot_running()
    fresh   = is_bot_state_fresh()

    if running and fresh:
        log("[CHECK3] OK — bot running and state is fresh")
        state["fix_attempts"] = 0
        state["consecutive_failures"] = 0
        return True, state

    if state["fix_attempts"] >= MAX_RESTARTS:
        log(f"[CHECK3] HALT — {MAX_RESTARTS} restart attempts exhausted")
        return False, state

    if not running:
        log("[CHECK3] Bot not running — starting...")
    else:
        log(f"[CHECK3] State stale > {BOT_STALE_MINUTES} min — restarting...")
        kill_python()

    start_bot()
    state["fix_attempts"] = state.get("fix_attempts", 0) + 1
    state["total_fixes"]  = state.get("total_fixes", 0) + 1
    state["last_fix"]     = datetime.now().isoformat()
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1

    append_report({
        "time": datetime.now().isoformat(),
        "action": "bot_restart",
        "attempt": state["fix_attempts"],
        "running_before": running,
        "state_fresh": fresh,
    })
    return False, state


# ── CHECK 4: Infra Guardian ──────────────────────────────────────────────────
def check_infra() -> bool:
    log("[CHECK4] Infra guardian...")
    ok = True

    # Rotate large log files
    for log_path in LOGS.glob("*.log"):
        size_mb = log_path.stat().st_size / (1024 * 1024)
        if size_mb > LOG_ROTATE_MB:
            archive = log_path.with_suffix(f".{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
            shutil.move(str(log_path), str(archive))
            log(f"[CHECK4] Rotated {log_path.name} ({size_mb:.0f}MB) -> {archive.name}")

    # Disk space
    try:
        usage = shutil.disk_usage(str(BASE))
        free_gb = usage.free / (1024 ** 3)
        if free_gb < DISK_WARN_GB:
            log(f"[CHECK4] WARN: Low disk space — {free_gb:.2f}GB free")
            ok = False
        else:
            log(f"[CHECK4] OK — {free_gb:.1f}GB free")
    except Exception as e:
        log(f"[CHECK4] Disk check error: {e}")

    return ok


# ── CHECK 5: Reporter ────────────────────────────────────────────────────────
def check_reporter(state: dict) -> dict:
    log("[CHECK5] Reporter...")
    now = datetime.now()

    # SMS on 3+ consecutive failures
    failures = state.get("consecutive_failures", 0)
    last_alert = state.get("last_alert")
    alert_cooldown = 30  # minutes between alerts

    if failures >= 3:
        send_alert = True
        if last_alert:
            try:
                last_dt = datetime.fromisoformat(last_alert)
                if (now - last_dt).total_seconds() / 60 < alert_cooldown:
                    send_alert = False
            except Exception:
                pass
        if send_alert:
            err_tail = tail_log(ERROR_LOG, lines=5)
            msg = f"FXPulse ALERT: {failures} consecutive failures.\nLast errors:\n{err_tail[:300]}"
            send_sms(msg)
            state["last_alert"] = now.isoformat()
            log(f"[CHECK5] Alert SMS sent — {failures} failures")

    # Daily 7am AEST summary
    aest_hour = (now.utctimetuple().tm_hour + 10) % 24
    last_daily = state.get("last_daily_report")
    due_today  = now.strftime("%Y-%m-%d")

    if aest_hour == DAILY_REPORT_HOUR and last_daily != due_today:
        bot_state_data = {}
        if BOT_STATE.exists():
            try:
                bot_state_data = json.loads(BOT_STATE.read_text())
            except Exception:
                pass
        balance  = bot_state_data.get("account", {}).get("balance", "?")
        perf     = bot_state_data.get("performance", {})
        wins     = perf.get("wins", 0)
        losses   = perf.get("losses", 0)
        pnl      = perf.get("total_pnl", 0)
        wr       = perf.get("win_rate", 0)
        msg = (f"FXPulse Daily — {now.strftime('%Y-%m-%d')}\n"
               f"Balance: ${balance}\nPnL: {pnl:+.2f}\n"
               f"Trades: {wins+losses} | WR: {wr:.0%}\n"
               f"Fixes today: {state.get('total_fixes', 0)}")
        send_sms(msg)
        state["last_daily_report"] = due_today
        log(f"[CHECK5] Daily report sent")

    return state


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    log("=" * 55)
    log("[AGENT] FXPulse Agent starting...")

    state = load_state()

    check_github_push()
    check_dashboard()
    ok, state = check_bot_guardian(state)
    check_infra()
    state = check_reporter(state)

    save_state(state)
    log(f"[AGENT] Done. Fixes total={state['total_fixes']} consecutive_failures={state['consecutive_failures']}")
    log("=" * 55)


if __name__ == "__main__":
    main()
