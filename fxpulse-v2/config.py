"""
config.py — FXPulse v2 shared configuration
All agents import from here. Credentials loaded from .env.
"""
import os

def _load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── MT5 ──────────────────────────────────────────────────────────────────────
MT5_LOGIN    = int(os.environ.get("MT5_LOGIN",    "0"))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER   = os.environ.get("MT5_SERVER",   "Pepperstone-Demo")

# ── Trading ───────────────────────────────────────────────────────────────────
PAPER_TRADING      = True   # Never change here — override in .env
CONFIDENCE_MIN     = 0.65   # Minimum signal confidence to act on
TIMEFRAME          = "M15"  # Brain scans M15 candles
CANDLES            = 100    # History depth per symbol
SCAN_INTERVAL      = 60     # Seconds between brain scans

# ── 28 Major Pairs ────────────────────────────────────────────────────────────
SYMBOLS = [
    "EURUSD.a", "GBPUSD.a", "USDJPY.a", "AUDUSD.a",
    "USDCAD.a", "NZDUSD.a", "USDCHF.a", "EURGBP.a",
    "EURJPY.a", "GBPJPY.a", "XAUUSD.a", "EURCAD.a",
    "AUDCAD.a", "AUDNZD.a", "AUDCHF.a", "CADCHF.a",
    "NZDCAD.a", "NZDCHF.a", "NZDJPY.a", "EURNZD.a",
    "EURAUD.a", "GBPAUD.a", "GBPCAD.a", "GBPNZD.a",
    "GBPCHF.a", "EURCHF.a", "CADJPY.a", "USDZAR.a",
]

# ── Currencies for strength basket ────────────────────────────────────────────
CURRENCIES = ["EUR", "USD", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SIGNALS_FILE = os.path.join(BASE_DIR, "data", "signals.json")
STATE_FILE   = os.path.join(BASE_DIR, "data", "bot_state.json")
LOG_DIR      = os.path.join(BASE_DIR, "logs")

# ── Dashboard push ────────────────────────────────────────────────────────────
RECEIVER_URL = "https://myforexpulse.com/data/receiver.php"
RECEIVER_KEY = "fxpulse2026"

# ── Alerts ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWILIO_SID       = os.environ.get("TWILIO_SID",       "")
TWILIO_TOKEN     = os.environ.get("TWILIO_TOKEN",      "")
TWILIO_FROM      = os.environ.get("TWILIO_FROM",       "")
ALERT_PHONE      = "+61431274377"
