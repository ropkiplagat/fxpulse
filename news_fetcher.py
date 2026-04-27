"""
FXPulse News Fetcher — Forex Factory calendar every 5 minutes.
Filters HIGH/MEDIUM impact events for USD, EUR, GBP, JPY, AUD, CAD.
Pushes news.json to GitHub; cron_pull.php serves it to dashboard.
"""
import os
import sys
import json
import base64
import requests
from datetime import datetime, timedelta, timezone

# ── Env loading (same pattern as config.py) ──────────────────────────────────
def _load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── Config ────────────────────────────────────────────────────────────────────
FF_URL         = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CURRENCIES     = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD"}
IMPACT_FILTER  = {"High", "Medium"}
GITHUB_REPO    = "ropkiplagat/fxpulse"
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
LOCAL_OUT      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "news.json")
_news_sha      = None


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_ff():
    r = requests.get(FF_URL, timeout=15, headers={"User-Agent": "FXPulse-News/1.0"})
    r.raise_for_status()
    return r.json()


# ── Filter ────────────────────────────────────────────────────────────────────
def filter_events(raw: list) -> list:
    now        = datetime.now(timezone.utc)
    look_back  = now - timedelta(hours=1)    # include recent-past events
    look_ahead = now + timedelta(hours=24)

    events = []
    for e in raw:
        if e.get("country", "").upper() not in CURRENCIES:
            continue
        if e.get("impact", "") not in IMPACT_FILTER:
            continue
        try:
            dt = datetime.fromisoformat(e["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt < look_back or dt > look_ahead:
            continue

        diff_min = int((dt - now).total_seconds() / 60)
        events.append({
            "time_utc":  dt.isoformat(),
            "currency":  e.get("country", "").upper(),
            "title":     e.get("title", ""),
            "impact":    e.get("impact", "").upper(),
            "forecast":  e.get("forecast", "") or "",
            "previous":  e.get("previous", "") or "",
            "actual":    e.get("actual",   "") or "",
            "in_min":    diff_min,
        })

    events.sort(key=lambda x: x["time_utc"])
    return events


# ── GitHub push ───────────────────────────────────────────────────────────────
def _gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "FXPulse-News/1.0",
    }


def push_github(events: list) -> bool:
    global _news_sha
    if not GITHUB_TOKEN:
        print("[NEWS] No GITHUB_TOKEN — push skipped")
        return False

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    payload = {
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "events":      events,
    }
    content = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()

    if not _news_sha:
        try:
            r = requests.get(api_url, headers=_gh_headers(), timeout=10)
            if r.status_code == 200:
                _news_sha = r.json().get("sha", "")
        except Exception:
            pass

    body = {
        "message": f"news {datetime.now(timezone.utc).strftime('%H:%M')} UTC",
        "content": content,
    }
    if _news_sha:
        body["sha"] = _news_sha

    try:
        r = requests.put(api_url, headers=_gh_headers(), json=body, timeout=15)
        if r.status_code in (200, 201):
            _news_sha = r.json()["content"]["sha"]
            print(f"[NEWS] GitHub push OK — {len(events)} events")
            return True
        if r.status_code == 409:
            _news_sha = None
        print(f"[NEWS] GitHub push failed: {r.status_code}")
        return False
    except Exception as e:
        print(f"[NEWS] GitHub push error: {e}")
        return False


# ── Save local copy ───────────────────────────────────────────────────────────
def save_local(events: list):
    os.makedirs(os.path.dirname(LOCAL_OUT), exist_ok=True)
    with open(LOCAL_OUT, "w", encoding="utf-8") as f:
        json.dump({"fetched_utc": datetime.now(timezone.utc).isoformat(), "events": events}, f, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[NEWS] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC — fetching FF calendar")
    try:
        raw    = fetch_ff()
        events = filter_events(raw)
        print(f"[NEWS] {len(events)} events in window (last 1h + next 24h) for {','.join(CURRENCIES)}")
        save_local(events)
        push_github(events)
    except requests.RequestException as e:
        print(f"[NEWS] Fetch error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[NEWS] Unexpected error: {e}")
        sys.exit(1)
