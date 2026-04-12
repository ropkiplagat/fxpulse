"""
SiteGround API Bridge — bot pushes bot_state.json to GitHub repo.
SiteGround cron_pull.php fetches raw file every minute → writes bot_state.json locally.
Uses 'repo' scope token (already configured) — no Gist needed.
"""
import requests
import json
import base64
from datetime import datetime, timezone
import config

PUSH_INTERVAL = 60  # seconds between pushes
_last_push = None
_file_sha = None  # cached SHA for GitHub API updates

REPO      = "ropkiplagat/fxpulse"
FILE_PATH = "bot_state.json"
RAW_URL   = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}"
API_URL   = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"


def _get_headers():
    token = getattr(config, "GITHUB_TOKEN", "")
    return {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "FXPulse-Bot/1.0",
    }


def _get_sha() -> str:
    """Fetch current SHA of bot_state.json in repo (needed for updates)."""
    global _file_sha
    if _file_sha:
        return _file_sha
    try:
        resp = requests.get(API_URL, headers=_get_headers(), timeout=10)
        if resp.status_code == 200:
            _file_sha = resp.json().get("sha", "")
        # 404 = file doesn't exist yet (first push) — that's fine
    except Exception:
        pass
    return _file_sha or ""


def push_state(state: dict) -> bool:
    """
    Push bot state to GitHub repo as bot_state.json.
    SiteGround cron_pull.php fetches it every minute.
    Returns True on success.
    """
    global _last_push, _file_sha

    token = getattr(config, "GITHUB_TOKEN", "")
    if not token:
        return False

    try:
        content = base64.b64encode(
            json.dumps(state, default=str).encode()
        ).decode()

        sha = _get_sha()
        payload = {
            "message": "bot state update",
            "content": content,
        }
        if sha:
            payload["sha"] = sha  # required for updates; omit for first create

        resp = requests.put(API_URL, headers=_get_headers(), json=payload, timeout=15)

        if resp.status_code in (200, 201):
            _file_sha = resp.json()["content"]["sha"]  # cache new SHA
            _last_push = datetime.now(timezone.utc)
            return True

        print(f"[SG] Push failed: {resp.status_code} {resp.text[:200]}")
        return False

    except Exception as e:
        print(f"[SG] Push failed: {e}")
        return False
