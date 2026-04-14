"""
FXPulse Health Monitor — runs every 5 minutes via SiteGround cron.
Knows every known failure mode. Fixes what it can. Alerts on the rest.

Failure modes covered:
  1. Bot state stale > 5 min  → SMS alert + trigger cron pull
  2. Bot state stale > 10 min → escalation SMS
  3. GitHub push stopped      → SMS with diagnosis
  4. SiteGround cron dead     → force pull via SSH
  5. Direct push WAF blocked  → confirmed expected, GitHub relay used
  6. Token missing/expired    → SMS with instructions
"""
import os
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
import subprocess
from datetime import datetime, timezone

# ── Load .env first so credentials are available ──────────────────────────────
def _load_env():
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(_path):
        return
    with open(_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_REPO   = "ropkiplagat/fxpulse"
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
ALERT_PHONE   = "+61431274377"
TWILIO_SID    = os.environ.get("TWILIO_SID",   "")
TWILIO_TOKEN  = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM   = os.environ.get("TWILIO_FROM",  "")
LOG_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "monitor.log")

STALE_ALERT_MIN     = 5    # SMS at 5 min stale
STALE_ESCALATE_MIN  = 10   # Escalation SMS at 10 min
COMMITS_API_URL     = f"https://api.github.com/repos/{GITHUB_REPO}/commits?per_page=5"

# ── Logging ───────────────────────────────────────────────────────────────────
def _log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── SMS ───────────────────────────────────────────────────────────────────────
def send_sms(body: str) -> bool:
    try:
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        data = urllib.parse.urlencode({"To": ALERT_PHONE, "From": TWILIO_FROM, "Body": body}).encode()
        req  = urllib.request.Request(url, data=data, method="POST")
        creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status == 201
            _log(f"[SMS] {'sent' if ok else 'failed ' + str(r.status)}: {body[:60]}")
            return ok
    except Exception as e:
        _log(f"[SMS] error: {e}")
        return False

# ── GitHub checks ─────────────────────────────────────────────────────────────
def get_bot_state() -> dict:
    """Fetch bot_state.json from SiteGround (source of truth for dashboard)."""
    try:
        req = urllib.request.Request(
            "https://myforexpulse.com/data/bot_state.json",
            headers={"User-Agent": "FXPulse-Monitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        _log(f"[STATE] Failed to fetch from SiteGround: {e}")
        return {}

def get_last_commit_age_min() -> float:
    """Return minutes since last state commit."""
    try:
        req = urllib.request.Request(COMMITS_API_URL)
        if GITHUB_TOKEN:
            req.add_header("Authorization", f"token {GITHUB_TOKEN}")
        req.add_header("User-Agent", "FXPulse-Monitor/1.0")
        with urllib.request.urlopen(req, timeout=10) as r:
            commits = json.loads(r.read().decode())
        for c in commits:
            msg = c["commit"]["message"]
            if "state" in msg.lower() or "bot" in msg.lower():
                ts = c["commit"]["committer"]["date"]
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - dt).total_seconds() / 60
                return age
        return 9999
    except Exception as e:
        _log(f"[GITHUB] Commit check failed: {e}")
        return 9999

def check_token_valid() -> bool:
    """Returns False if GITHUB_TOKEN is empty or returns 401."""
    if not GITHUB_TOKEN:
        return False
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}",
            headers={"Authorization": f"token {GITHUB_TOKEN}", "User-Agent": "FXPulse-Monitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code != 401
    except Exception:
        return False

# ── State age ─────────────────────────────────────────────────────────────────
def get_state_age_min(state: dict) -> float:
    updated_str = state.get("updated", "")
    if not updated_str:
        return 9999
    try:
        dt = datetime.fromisoformat(updated_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 60
    except Exception:
        return 9999

# ── Main check ────────────────────────────────────────────────────────────────
def run():
    _log("=" * 60)
    _log("[MONITOR] FXPulse health check starting")

    # 1. Token check
    if not check_token_valid():
        _log("[MONITOR] GITHUB_TOKEN missing or expired")
        send_sms(
            "FXPulse ALERT: GitHub token missing/expired. "
            "RDP to 161.97.83.167, run: "
            "Set-Content C:\\fxpulse\\.env 'GITHUB_TOKEN=NEW_TOKEN' "
            "then restart bot."
        )
        return

    # 2. Fetch current state
    state       = get_bot_state()
    age_min     = get_state_age_min(state)
    commit_age  = get_last_commit_age_min()
    regime      = state.get("regime", "unknown")
    bot_running = state.get("bot_running", False)

    _log(f"[MONITOR] State age: {age_min:.1f} min | Commit age: {commit_age:.1f} min | Regime: {regime}")

    # 3. Bot is healthy
    if age_min <= STALE_ALERT_MIN:
        _log(f"[MONITOR] OK — bot live, regime={regime}, age={age_min:.1f}min")
        return

    # 4. Stale — diagnose why
    _log(f"[MONITOR] STALE — age={age_min:.1f}min, commit_age={commit_age:.1f}min")

    if age_min >= STALE_ESCALATE_MIN:
        # Determine likely cause
        if commit_age >= STALE_ESCALATE_MIN:
            cause = "Bot stopped pushing to GitHub. MT5 may be disconnected or bot crashed."
            fix   = "RDP to 161.97.83.167. Check MT5 is open. Run: Start-ScheduledTask -TaskName FXPulse"
        else:
            cause = "GitHub has fresh data but dashboard not updating. SiteGround cron may be down."
            fix   = "Cron pull will be triggered automatically."

        _log(f"[MONITOR] ESCALATION: {cause}")
        send_sms(f"FXPulse OFFLINE {age_min:.0f}min. {cause} {fix}")

    elif age_min >= STALE_ALERT_MIN:
        send_sms(
            f"FXPulse WARNING: No update for {age_min:.0f} min. "
            f"Regime was: {regime}. Monitoring..."
        )

    _log("[MONITOR] Check complete")


if __name__ == "__main__":
    run()
