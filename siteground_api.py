"""
SiteGround API Bridge.
Strategy:
  1. Try direct HTTPS POST to myforexpulse.com/state_push.php
  2. If that fails, fall back to GitHub relay (cron pulls every minute)
"""
import requests
import json
import base64
from datetime import datetime, timezone
import config

PUSH_URL      = "https://myforexpulse.com/api/bot_push.php"
PUSH_INTERVAL = 60
_last_push    = None
_file_sha     = None

# GitHub fallback
REPO     = "ropkiplagat/fxpulse"
API_URL  = f"https://api.github.com/repos/{REPO}/contents/bot_state.json"


def _gh_headers():
    return {
        "Authorization": f"token {getattr(config, 'GITHUB_TOKEN', '')}",
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "FXPulse-Bot/1.0",
    }


def _get_sha() -> str:
    global _file_sha
    if _file_sha:
        return _file_sha
    try:
        r = requests.get(API_URL, headers=_gh_headers(), timeout=10)
        if r.status_code == 200:
            _file_sha = r.json().get("sha", "")
    except Exception:
        pass
    return _file_sha or ""


def _push_direct(state: dict) -> bool:
    """POST directly to SiteGround endpoint."""
    try:
        payload = {
            "api_key": getattr(config, "API_KEY", ""),
            "data":    json.dumps(state, default=str),
        }
        r = requests.post(PUSH_URL, json=payload, timeout=10)
        if r.status_code == 200 and r.text.strip() == "OK":
            print("[SG] Direct push OK")
            return True
        print(f"[SG] Direct push failed: {r.status_code} {r.text[:100]}")
        return False
    except Exception as e:
        print(f"[SG] Direct push error: {e}")
        return False


def _push_github(state: dict) -> bool:
    """PUT to GitHub repo as fallback."""
    global _file_sha, _last_push
    token = getattr(config, "GITHUB_TOKEN", "")
    if not token:
        return False
    try:
        content = base64.b64encode(json.dumps(state, default=str).encode()).decode()
        sha     = _get_sha()
        payload = {"message": f"state {datetime.now(timezone.utc).strftime('%H:%M:%S')}", "content": content}
        if sha:
            payload["sha"] = sha
        r = requests.put(API_URL, headers=_gh_headers(), json=payload, timeout=15)
        if r.status_code in (200, 201):
            _file_sha = r.json()["content"]["sha"]
            print("[SG] GitHub push OK")
            return True
        if r.status_code == 409:
            _file_sha = None
        print(f"[SG] GitHub push failed: {r.status_code}")
        return False
    except Exception as e:
        print(f"[SG] GitHub push error: {e}")
        return False


def push_state(state: dict) -> bool:
    global _last_push
    ok = _push_direct(state) or _push_github(state)
    if ok:
        _last_push = datetime.now(timezone.utc)
    return ok


# Per-user SHA cache
_user_shas: dict = {}

def push_user_state(username: str, state: dict) -> bool:
    """Push per-user MT5 state to GitHub → SiteGround cron pulls it."""
    token = getattr(config, "GITHUB_TOKEN", "")
    if not token:
        return False
    path    = f"user_states/{username}.json"
    api_url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    try:
        content = base64.b64encode(json.dumps(state, default=str).encode()).decode()
        sha     = _user_shas.get(username)
        if not sha:
            try:
                r = requests.get(api_url, headers=_gh_headers(), timeout=8)
                if r.status_code == 200:
                    sha = r.json().get("sha", "")
                    _user_shas[username] = sha
            except Exception:
                pass
        payload = {
            "message": f"user state {username} {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
            "content": content,
        }
        if sha:
            payload["sha"] = sha
        r = requests.put(api_url, headers=_gh_headers(), json=payload, timeout=15)
        if r.status_code in (200, 201):
            _user_shas[username] = r.json()["content"]["sha"]
            print(f"[SG] User state push OK — {username}")
            return True
        if r.status_code == 409:
            _user_shas.pop(username, None)
        print(f"[SG] User state push failed {username}: {r.status_code}")
        return False
    except Exception as e:
        print(f"[SG] User state push error {username}: {e}")
        return False
