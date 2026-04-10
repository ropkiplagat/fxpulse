"""
Forex Bot Configuration
Pepperstone MT5 — Demo account for testing
"""

# === MT5 Connection ===
# Leave blank — run: python security.py --setup to encrypt credentials securely
MT5_LOGIN = 0          # Your Pepperstone demo account number
MT5_PASSWORD = ""      # Your password (use security.py to encrypt)
MT5_SERVER = "Pepperstone-Demo"  # Server name from MT5 login screen

# === Paper Trading Mode ===
PAPER_TRADING         = True    # START HERE — set False only after demo success
PAPER_STARTING_BALANCE = 10_000.0  # Virtual starting balance

# === Trading Symbols (Pepperstone .a suffix) ===
MAJOR_CURRENCIES = ["EURUSD.a", "GBPUSD.a", "USDJPY.a", "USDCHF.a", "USDCAD.a", "AUDUSD.a", "NZDUSD.a"]
MINOR_CURRENCIES = ["EURGBP.a", "EURJPY.a", "GBPJPY.a", "AUDJPY.a", "CADJPY.a", "GBPCHF.a", "EURAUD.a"]
EXOTIC_CURRENCIES = ["USDTRY.a", "USDZAR.a", "USDMXN.a", "USDSEK.a", "USDNOK.a"]
COMMODITIES      = ["XAUUSD.a", "US500.a", "NAS100.a", "UK100.a"]

# 8 currencies used for strength calculation
STRENGTH_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]

# === Timeframes ===
TF_FAST   = "M15"   # Signal timeframe
TF_SLOW   = "H1"    # Confirmation timeframe
RENKO_TF  = "M1"    # Source data for Renko simulation
NUM_BARS  = 200     # Bars to fetch per symbol

# === Risk Management ===
RISK_PERCENT          = 1.0    # % of account per trade
MAX_DAILY_DRAWDOWN    = 5.0    # % — halt trading if exceeded
MAX_SPREAD_PIPS       = 3.0    # Skip trade if spread > this
MAGIC_NUMBER          = 20001
SLIPPAGE              = 10

# === AI Predictor ===
MIN_WIN_PROBABILITY   = 0.65   # Only trade if AI confidence >= 65%
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
MIN_STRENGTH_GAP     = 1.5    # Min strength difference between currencies
MIN_CONFLUENCE_SCORE = 0.60   # Minimum signal confluence score
TOP_PAIRS_COUNT      = 3      # Show top N pairs

# === Cooldown ===
COOLDOWN_MINUTES      = 15    # Wait N min after closing a trade on a symbol
MAX_CONSECUTIVE_LOSSES = 3    # Pause after N consecutive losses

# === Logging ===
PERFORMANCE_FILE = "logs/performance.csv"
SIGNAL_LOG_FILE  = "logs/signals.csv"
BOT_STATE_FILE   = "logs/bot_state.json"

# === Telegram Alerts (optional) ===
TELEGRAM_TOKEN   = ""   # Get from @BotFather
TELEGRAM_CHAT_ID = ""   # Your chat ID (message @userinfobot)

# === LSTM Ensemble ===
USE_LSTM = True         # Set False to use XGBoost only (faster)
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

# === SiteGround Web Dashboard (friend/client can view from any browser) ===
# 1. Upload deploy/receiver.php to your SiteGround public_html folder
# 2. Set the URL and a secret key below (same key goes in receiver.php)
SITEGROUND_API_URL = "https://myforexpulse.com/api/bot_push.php"
SITEGROUND_API_KEY = "0d070602123b2dbf102ab30f01d95f34cab48bf4e08cabd8dd5b53561d6cdac7"

# === Kelly Criterion Position Sizing ===
USE_KELLY_SIZING = True      # Set False to use flat RISK_PERCENT instead
