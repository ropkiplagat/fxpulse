"""
Forex Bot Configuration
Pepperstone MT5 — Live trading
"""
import os as _os

def _load_env():
    _path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".env")
    if not _os.path.exists(_path):
        return
    with open(_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _os.environ.setdefault(_k.strip(), _v.strip())

_load_env()

# === MT5 Connection ===
MT5_LOGIN         = int(_os.environ.get("MT5_LOGIN", "0"))
MT5_PASSWORD      = _os.environ.get("MT5_PASSWORD", "")
MT5_SERVER        = _os.environ.get("MT5_SERVER", "Pepperstone-Demo")
MT5_TERMINAL_PATH = _os.environ.get("MT5_TERMINAL_PATH", r"C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe")

# Encryption secret — MUST match ENCRYPT_SECRET in deploy/includes/config.php on SiteGround
MT5_ENCRYPT_SECRET = _os.environ.get("MT5_ENCRYPT_SECRET", "fxpulse-mt5-enc-v1-changeme-on-server")

# === Paper Trading Mode ===
PAPER_TRADING         = True    # Paper trading — build track record before going live
PAPER_STARTING_BALANCE = 10_000.0  # Virtual starting balance

# === Trading Symbols (Pepperstone .a suffix) ===
MAJOR_CURRENCIES = ["EURUSD.a", "GBPUSD.a", "USDJPY.a", "USDCHF.a", "USDCAD.a", "AUDUSD.a", "NZDUSD.a"]
MINOR_CURRENCIES = ["EURGBP.a", "EURJPY.a", "GBPJPY.a", "AUDJPY.a", "CADJPY.a", "GBPCHF.a", "EURAUD.a"]
EXOTIC_CURRENCIES = ["USDTRY.a", "USDZAR.a", "USDMXN.a", "USDSEK.a", "USDNOK.a"]
COMMODITIES      = ["XAUUSD.a", "US500.a", "NAS100.a", "UK100.a"]

# 9 assets used for strength calculation (8 forex + Gold)
STRENGTH_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "XAU"]

# === Timeframes ===
TF_FAST   = "M15"   # Signal timeframe
TF_SLOW   = "H1"    # Confirmation timeframe
RENKO_TF  = "M1"    # Source data for Renko simulation
NUM_BARS  = 200     # Bars to fetch per symbol

# === Risk Management ===
RISK_PERCENT          = 0.5    # % of account per trade (Bethwel trial spec)
MAX_DAILY_DRAWDOWN    = 2.0    # % — halt new entries if daily P&L hits -2%
MAX_CONCURRENT_TRADES = 6      # Max simultaneous open positions (Bethwel trial spec)
MAX_SPREAD_PIPS       = 3.0    # Skip trade if spread > this
MARGIN_MIN_FREE_RATIO = 0.30   # Skip all trades if free_margin/equity < 30%
MAGIC_NUMBER          = 20001
SLIPPAGE              = 10

# === AI Predictor ===
# 28 April 2026 — Phase 2 matrix backtest deployment
# Production model outputs 0.3-2%; previous prob=0.65 was unreachable (model ceiling ~26%)
# gap=0.135 + prob=0.05 → best risk-adjusted cell in Phase 2 matrix (WR=55.6%, PF=2.44, DD=1.99%)
# Week-2: retrain model with class_weight=balanced; revisit prob threshold then
MIN_WIN_PROBABILITY   = 0.05   # Phase 2 deploy: model ceiling ~26%, prob=0.05 fires trades
MODEL_PATH            = "models/xgb_forex.pkl"
SCALER_PATH           = "models/scaler.pkl"
RETRAIN_EVERY_BARS    = 500    # Re-train after this many new bars

# === Renko Settings ===
RENKO_BRICK_ATR_PERIOD = 14    # ATR period for dynamic brick size
RENKO_BRICK_MULTIPLIER = 0.5   # Brick = ATR * multiplier
PULLBACK_MIN_BRICKS    = 2     # Min bricks for valid pullback
PULLBACK_MAX_BRICKS    = 4     # Max bricks before trend invalidated

# === Trade Management ===
PARTIAL_CLOSE_RATIO    = 0.5   # Close 50% at 1R
BREAKEVEN_AT_R         = 1.0   # Move SL to BE when +1R
TRAILING_BRICKS        = 2     # Trail SL by N Renko bricks
TP_R_MULTIPLE          = 2.0   # TP at 2R

# === Session Filter (UTC hours) ===
SESSIONS = {
    "london":   (7, 16),
    "new_york": (12, 21),
}
TRADE_IN_SESSIONS = ["london", "new_york"]  # Only trade these sessions
OVERLAP_BONUS = True  # Prefer London/NY overlap (12-16 UTC)

# === Confluence Thresholds ===
# MIN_STRENGTH_GAP recalibrated 27 April 2026 evening
# Previous value 1.5 was unreachable; currency_strength.py outputs in -0.2 to +0.2 range
# 0.135 = 90th percentile of 30-day strength gap distribution (Phase 1 analysis)
# Phase 2 multi-threshold backtest will validate this choice on 28 April 2026
# If Phase 2 finds a better value, this will be updated
MIN_STRENGTH_GAP     = 0.135  # Min strength difference between currencies
MIN_CONFLUENCE_SCORE = 0.60   # Minimum signal confluence score
TOP_PAIRS_COUNT      = 3      # Show top N pairs

# === Cooldown ===
COOLDOWN_MINUTES      = 15    # Wait N min after closing a trade on a symbol
MAX_CONSECUTIVE_LOSSES = 3    # Pause after N consecutive losses

# === Logging ===
PERFORMANCE_FILE = "logs/performance.csv"
SIGNAL_LOG_FILE  = "logs/signals.csv"
BOT_STATE_FILE   = "logs/bot_state.json"

# === Telegram Alerts ===
TELEGRAM_TOKEN       = _os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SUBSCRIBERS = _os.environ.get("TELEGRAM_SUBSCRIBERS", "")  # comma-separated chat_ids

# === LSTM Ensemble ===
USE_LSTM = False        # Disabled — TensorFlow training hangs on this VPS; XGBoost sufficient
LSTM_WEIGHT = 0.35      # LSTM weight in ensemble (XGB gets 1 - this)
XGB_WEIGHT  = 0.65      # XGBoost weight

# === Regime Filter ===
SKIP_NON_TRENDING_REGIMES = True   # Don't trade in ranging/volatile/crisis

# === News Filter ===
USE_NEWS_FILTER = True  # Block trades during high-impact news

# === Correlation Filter ===
USE_CORRELATION_FILTER = True  # Block correlated duplicate trades

# === Web Dashboard ===
WEB_DASHBOARD_PORT = 5000

# === Direct push to SiteGround dashboard (no GitHub relay) ===
API_KEY = _os.environ.get("API_KEY", "0d070602123b2dbf102ab30f01d95f34cab48bf4e08cabd8dd5b53561d6cdac7")

# === GitHub Push — bot_state.json → repo → SiteGround cron fetches it ===
GITHUB_REPO  = "ropkiplagat/fxpulse"
GITHUB_TOKEN = _os.environ.get("GITHUB_TOKEN", "")

# === Kelly Criterion Position Sizing ===
USE_KELLY_SIZING = True      # Set False to use flat RISK_PERCENT instead
