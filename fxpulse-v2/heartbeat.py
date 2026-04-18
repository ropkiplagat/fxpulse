"""
heartbeat.py — FXPulse v2 | Agent 4: Heartbeat
===============================================
Pushes a heartbeat record to GitHub every 30s.
monitor.py checks GitHub — if heartbeat.json > 5 min stale, fires alert.

GATE 6 acceptance test:
  fxpulse-v2/data/heartbeat.json on GitHub updates every 30 seconds.
"""

import os
import sys
import json
import time
import base64
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
        logging.FileHandler(os.path.join(config.LOG_DIR, "heartbeat.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("heartbeat")

PING_INTERVAL = 30
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
REPO          = "ropkiplagat/fxpulse"
HB_PATH       = "fxpulse-v2/data/heartbeat.json"
_hb_sha       = None   # cached sha to avoid extra GET each push


def _signals_summary() -> dict:
    try:
        with open(config.SIGNALS_FILE) as f:
            d = json.load(f)
        return {
            "scanned":    d.get("scanned", 0),
            "actionable": len(d.get("signals", [])),
            "top":        d["signals"][0]["symbol"] if d.get("signals") else None,
        }
    except Exception:
        return {"scanned": 0, "actionable": 0, "top": None}


def _push_heartbeat() -> bool:
    global _hb_sha
    if not GITHUB_TOKEN:
        log.warning("[HB] No GITHUB_TOKEN — cannot push heartbeat")
        return False

    summary = _signals_summary()
    payload = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "agent":      "heartbeat",
        "interval_s": PING_INTERVAL,
        **summary,
    }
    content = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()
    api     = f"https://api.github.com/repos/{REPO}/contents/{HB_PATH}"
    hdrs    = {"Authorization": f"token {GITHUB_TOKEN}", "User-Agent": "fxpulse-v2",
               "Content-Type": "application/json"}

    # get current sha if we don't have it cached
    if not _hb_sha:
        try:
            req = urllib.request.Request(api, headers=hdrs)
            res = json.loads(urllib.request.urlopen(req, timeout=8).read())
            _hb_sha = res.get("sha")
        except Exception:
            _hb_sha = None

    body = json.dumps({"message": "hb: alive", "content": content,
                        **( {"sha": _hb_sha} if _hb_sha else {})}).encode()
    try:
        req2 = urllib.request.Request(api, data=body, headers=hdrs, method="PUT")
        res2 = json.loads(urllib.request.urlopen(req2, timeout=15).read())
        _hb_sha = res2.get("content", {}).get("sha")   # cache new sha
        log.info(f"[HB] GitHub OK — scanned={summary['scanned']} actionable={summary['actionable']}")
        return True
    except Exception as e:
        _hb_sha = None   # reset so next attempt does GET
        log.warning(f"[HB] GitHub push failed: {e}")
        return False


def run():
    log.info("=" * 55)
    log.info("FXPulse v2 | Heartbeat starting")
    log.info(f"  Interval : {PING_INTERVAL}s")
    log.info(f"  Token    : {'set' if GITHUB_TOKEN else 'MISSING'}")
    log.info("=" * 55)

    while True:
        try:
            _push_heartbeat()
        except Exception as e:
            log.error(f"[HB] Unexpected: {e}", exc_info=True)
        time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    run()
