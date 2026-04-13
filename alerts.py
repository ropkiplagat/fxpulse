"""
Alert system — email and SMS notifications when bot goes offline.

Credentials go in C:\fxpulse\.env (one per line, KEY=value):
  GMAIL_USER=youraddress@gmail.com
  GMAIL_APP_PASSWORD=xxxxxxxxxxxx   (16-char App Password, not your login password)
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
  TWILIO_FROM_NUMBER=+1xxxxxxxxxx

.env overrides the defaults below. If .env is missing, defaults are used.
"""
import os
import json
import smtplib
import threading
import urllib.request
import urllib.parse
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

ALERT_EMAIL    = "ropkiplagat2@gmail.com"
ALERT_PHONE    = "+61431274377"
STALE_MINUTES  = 10   # alert if no state update for this many minutes
CHECK_INTERVAL = 300  # check every 5 minutes

_alert_sent = False   # prevent spam — reset when bot comes back online


def _load_env() -> dict:
    """Load C:\fxpulse\.env file."""
    env  = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def send_email_alert(last_updated: str) -> bool:
    """Send Gmail SMTP alert to ALERT_EMAIL."""
    env       = _load_env()
    gmail_user = env.get("GMAIL_USER", "")
    gmail_pass = env.get("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_pass:
        print("[ALERT] Gmail credentials missing in .env — skipping email")
        return False
    try:
        msg            = MIMEMultipart()
        msg["From"]    = gmail_user
        msg["To"]      = ALERT_EMAIL
        msg["Subject"] = "🚨 FXPulse Bot OFFLINE Alert"
        body = (
            f"FXPulse bot has gone offline.\n\n"
            f"Last data received: {last_updated}\n\n"
            f"Action required:\n"
            f"  1. RDP into VPS: 161.97.83.167\n"
            f"  2. Username: Administrator\n"
            f"  3. Open PowerShell and run:\n\n"
            f"     Stop-ScheduledTask -TaskName 'FXPulse'\n"
            f"     Start-ScheduledTask -TaskName 'FXPulse'\n\n"
            f"  Or double-click: C:\\fxpulse\\main.py\n\n"
            f"-- FXPulse Alert System"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, ALERT_EMAIL, msg.as_string())
        print(f"[ALERT] Email sent to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"[ALERT] Email failed: {e}")
        return False


def send_sms_alert(last_updated: str) -> bool:
    """Send Twilio SMS alert to ALERT_PHONE.
    Credential lookup order: .env file → OS environment → skip.
    """
    env         = _load_env()
    account_sid = env.get("TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token  = env.get("TWILIO_AUTH_TOKEN")  or os.environ.get("TWILIO_AUTH_TOKEN",  "")
    from_number = env.get("TWILIO_FROM_NUMBER") or os.environ.get("TWILIO_FROM_NUMBER", "")
    if not account_sid or not auth_token or not from_number:
        print("[ALERT] Twilio credentials missing in .env and environment — skipping SMS")
        return False
    try:
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        body = (
            f"FXPulse OFFLINE — last data: {last_updated}. "
            f"RDP to 161.97.83.167 and restart bot."
        )
        data = urllib.parse.urlencode({
            "To":   ALERT_PHONE,
            "From": from_number,
            "Body": body,
        }).encode()
        req   = urllib.request.Request(url, data=data, method="POST")
        creds = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 201:
                print(f"[ALERT] SMS sent to {ALERT_PHONE}")
                return True
            print(f"[ALERT] SMS HTTP {resp.status}")
    except Exception as e:
        print(f"[ALERT] SMS failed: {e}")
    return False


def check_state_age(state_file: str) -> tuple[bool, str]:
    """Returns (is_stale, last_updated_str). Stale = no update for STALE_MINUTES."""
    if not os.path.exists(state_file):
        return True, "never"
    try:
        with open(state_file) as f:
            state = json.load(f)
        updated_str = state.get("updated", "")
        if not updated_str:
            return True, "unknown"
        updated = datetime.fromisoformat(updated_str)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_min = (datetime.now(timezone.utc) - updated).total_seconds() / 60
        return age_min > STALE_MINUTES, updated_str
    except Exception:
        return True, "parse error"


class OfflineAlertThread(threading.Thread):
    """
    Background thread that runs every 5 minutes.
    Sends email + SMS if bot_state.json hasn't been updated for 10+ minutes.
    Resets automatically when bot comes back online.
    """
    def __init__(self, state_file: str):
        super().__init__(daemon=True, name="OfflineAlertThread")
        self.state_file = state_file
        self._stop      = threading.Event()

    def run(self):
        global _alert_sent
        print(f"[ALERT] Watchdog started — monitoring {self.state_file}")
        while not self._stop.is_set():
            self._stop.wait(CHECK_INTERVAL)
            if self._stop.is_set():
                break
            is_stale, last_updated = check_state_age(self.state_file)
            if is_stale and not _alert_sent:
                print(f"[ALERT] Bot offline (last: {last_updated}) — sending alerts")
                send_email_alert(last_updated)
                send_sms_alert(last_updated)
                _alert_sent = True
            elif not is_stale and _alert_sent:
                print("[ALERT] Bot back online — alert reset")
                _alert_sent = False

    def stop(self):
        self._stop.set()


if __name__ == "__main__":
    print(f"[TEST] Sending test SMS to {ALERT_PHONE} ...")
    ok = send_sms_alert("TEST — manual trigger")
    if ok:
        print("[TEST] SMS delivered successfully.")
    else:
        print("[TEST] SMS FAILED — check credentials / Twilio account.")
