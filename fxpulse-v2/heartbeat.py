"""
heartbeat.py — FXPulse v2 | Agent 4: Heartbeat
===============================================
Does ONE thing: POSTs a ping to receiver.php every 30s.
If receiver stops getting pings, monitor.py fires an alert.

GATE 6 acceptance test:
  receiver.php logs a heartbeat entry every 30 seconds.
"""

import os
import sys
import time
import json
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

PING_INTERVAL = 30   # seconds


def _read_signals_summary() -> dict:
    """Read current signals.json for status payload."""
    try:
        with open(config.SIGNALS_FILE) as f:
            data = json.load(f)
        # Use .a-aware symbol list from config
        return {
            "scanned":    data.get("scanned", 0),
            "actionable": len(data.get("signals", [])),
            "top_symbol": data["signals"][0]["symbol"] if data.get("signals") else None,
            "symbols_watched": len(config.SYMBOLS),   # 28 pairs, all .a suffix
        }
    except Exception:
        return {"scanned": 0, "actionable": 0, "top_symbol": None, "symbols_watched": len(config.SYMBOLS)}


def ping() -> bool:
    summary = _read_signals_summary()
    payload = json.dumps({
        "type":      "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "key":       config.RECEIVER_KEY,
        **summary,
    }).encode()

    req = urllib.request.Request(
        config.RECEIVER_URL,
        data=payload,
        headers={"Content-Type": "application/json", "X-FXPulse-Key": config.RECEIVER_KEY},
        method="POST",
    )
    try:
        res = urllib.request.urlopen(req, timeout=10)
        log.info(f"[HB] Ping OK — {res.status} | scanned={summary['scanned']} actionable={summary['actionable']}")
        return True
    except urllib.error.HTTPError as e:
        log.warning(f"[HB] Ping HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        log.warning(f"[HB] Ping failed: {e.reason}")
    except Exception as e:
        log.error(f"[HB] Ping error: {e}")
    return False


def run():
    log.info("=" * 55)
    log.info("FXPulse v2 | Heartbeat starting")
    log.info(f"  Receiver : {config.RECEIVER_URL}")
    log.info(f"  Interval : {PING_INTERVAL}s")
    log.info(f"  Symbols  : {len(config.SYMBOLS)} pairs (.a suffix)")
    log.info("=" * 55)

    while True:
        try:
            ping()
        except Exception as e:
            log.error(f"[HB] Unexpected error: {e}", exc_info=True)
        time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    run()
