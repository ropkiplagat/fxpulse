"""
monitor.py — FXPulse v2 | Agent 5: Monitor
===========================================
Checks heartbeat.json on GitHub every 60s.
If stale > 5 min → Telegram alert.
If stale > 10 min → escalation SMS via Twilio.

GATE 10 acceptance test:
  Kill brain.py. Within 6 minutes monitor logs "[MONITOR] ALERT fired".
"""

import os
import sys
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

import config

os.makedirs(config.LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_DIR, "monitor.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("monitor")

CHECK_INTERVAL    = 60       # seconds between checks
WARN_THRESHOLD    = 5 * 60   # 5 min — Telegram warning
ESCALATE_THRESHOLD= 10 * 60  # 10 min — SMS escalation

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO         = "ropkiplagat/fxpulse"
HB_PATH      = "fxpulse-v2/data/heartbeat.json"
SIG_PATH     = "fxpulse-v2/data/signals.json"

TELEGRAM_TOKEN   = config.TELEGRAM_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
TWILIO_SID       = config.TWILIO_SID
TWILIO_TOKEN     = config.TWILIO_TOKEN
TWILIO_FROM      = config.TWILIO_FROM
ALERT_PHONE      = config.ALERT_PHONE

_last_alert_level = 0   # 0=none, 1=telegram sent, 2=sms sent
_last_ok_log      = 0


def _fetch_github_json(path: str) -> dict | None:
    if not GITHUB_TOKEN:
        return None
    api  = f"https://api.github.com/repos/{REPO}/contents/{path}"
    hdrs = {"Authorization": f"token {GITHUB_TOKEN}", "User-Agent": "fxpulse-v2"}
    try:
        req = urllib.request.Request(api, headers=hdrs)
        res = json.loads(urllib.request.urlopen(req, timeout=10).read())
        import base64
        return json.loads(base64.b64decode(res["content"].replace("\n", "")).decode())
    except Exception as e:
        log.warning(f"[MONITOR] GitHub fetch {path} failed: {e}")
        return None


def _age_seconds(data: dict, key: str = "timestamp") -> float:
    ts = data.get(key)
    if not ts:
        return 9999.0
    try:
        t = datetime.fromisoformat(ts)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return 9999.0


def _send_telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("[MONITOR] Telegram not configured")
        return False
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    body = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}).encode()
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
        log.info("[MONITOR] Telegram sent")
        return True
    except Exception as e:
        log.error(f"[MONITOR] Telegram failed: {e}")
        return False


def _send_sms(msg: str) -> bool:
    if not TWILIO_SID or not TWILIO_TOKEN:
        log.warning("[MONITOR] Twilio not configured")
        return False
    import base64
    url   = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    body  = urllib.parse.urlencode({
        "From": TWILIO_FROM,
        "To":   ALERT_PHONE,
        "Body": msg,
    }).encode()
    try:
        import urllib.parse
        req = urllib.request.Request(url, data=body,
            headers={"Authorization": f"Basic {creds}",
                     "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
        log.info("[MONITOR] SMS sent")
        return True
    except Exception as e:
        log.error(f"[MONITOR] SMS failed: {e}")
        return False


def check_once():
    global _last_alert_level, _last_ok_log

    hb   = _fetch_github_json(HB_PATH)
    sig  = _fetch_github_json(SIG_PATH)

    hb_age  = _age_seconds(hb,  "timestamp") if hb  else 9999.0
    sig_age = _age_seconds(sig, "updated")   if sig else 9999.0

    now = time.time()

    # ── All good ──
    if hb_age < WARN_THRESHOLD:
        if now - _last_ok_log > 300:   # log OK every 5 min max
            log.info(f"[MONITOR] OK — heartbeat {hb_age:.0f}s ago | signals {sig_age:.0f}s ago")
            _last_ok_log = now
        if _last_alert_level > 0:
            log.info("[MONITOR] System recovered — resetting alert state")
            _send_telegram("✅ *FXPulse v2 RECOVERED* — heartbeat resumed")
            _last_alert_level = 0
        return

    # ── Level 1: Telegram warning ──
    if hb_age >= WARN_THRESHOLD and _last_alert_level < 1:
        age_min = hb_age / 60
        msg = (f"⚠️ *FXPulse v2 WARNING*\n"
               f"Heartbeat silent for {age_min:.1f} minutes.\n"
               f"Check brain.py and heartbeat.py on VPS.")
        log.warning(f"[MONITOR] ALERT fired — heartbeat {age_min:.1f}min stale")
        _send_telegram(msg)
        _last_alert_level = 1

    # ── Level 2: SMS escalation ──
    if hb_age >= ESCALATE_THRESHOLD and _last_alert_level < 2:
        age_min = hb_age / 60
        msg = f"FXPulse v2 DOWN {age_min:.0f}min. Check VPS 161.97.83.167. RDP in and restart tasks."
        log.warning(f"[MONITOR] ESCALATION — SMS firing")
        _send_sms(msg)
        _last_alert_level = 2


def run():
    log.info("=" * 55)
    log.info("FXPulse v2 | Monitor starting")
    log.info(f"  Check interval : {CHECK_INTERVAL}s")
    log.info(f"  Warn threshold : {WARN_THRESHOLD//60}min")
    log.info(f"  Escalate       : {ESCALATE_THRESHOLD//60}min → SMS")
    log.info(f"  Telegram       : {'configured' if TELEGRAM_TOKEN else 'NOT SET'}")
    log.info(f"  Twilio         : {'configured' if TWILIO_SID else 'NOT SET'}")
    log.info("=" * 55)

    while True:
        try:
            check_once()
        except Exception as e:
            log.error(f"[MONITOR] Check failed: {e}", exc_info=True)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
