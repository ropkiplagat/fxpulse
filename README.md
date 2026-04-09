# FXPulse — AI Forex Trading Bot

An algorithmic forex trading bot for Pepperstone MT5 combining currency strength analysis, Renko price action, XGBoost + LSTM ensemble AI, and a live web dashboard.

---

## Features

- **Currency Strength Engine** — ranks all 8 major currencies (USD, EUR, GBP, JPY, AUD, NZD, CAD, CHF) from M15 + H1 data every 60 seconds
- **Renko Signal Detection** — pullback entries on Renko charts (ATR-dynamic brick size)
- **AI Ensemble Predictor** — XGBoost + optional LSTM; only trades when win probability >= 65%
- **Kelly Criterion Sizing** — position size adapts to recent win rate and R:R
- **Full Trade Management** — partial close at 1R, break-even at 1R, Renko trailing stop, 2R TP
- **Regime Filter** — skips ranging, high-volatility, and crisis market conditions
- **News Filter** — blocks trades during high-impact economic events
- **Correlation Filter** — prevents duplicate correlated trades running simultaneously
- **Paper Trading Mode** — safe simulation with virtual balance before going live
- **Telegram Alerts** — instant push notifications for signals, entries, and exits
- **Web Dashboard** — live status page deployable to SiteGround (PHP + JSON push)
- **Watchdog** — auto-restarts on crash, respects daily drawdown limit

---

## Architecture

```
forex-bot/
├── main.py               # Entry point — main trading loop
├── config.py             # All settings (edit this first)
├── mt5_connector.py      # MT5 connection + order execution
├── currency_strength.py  # 8-currency strength ranking
├── renko.py              # Renko simulation from M1 bars
├── signals.py            # Signal confluence scoring
├── ai_predictor.py       # XGBoost win probability model
├── lstm_predictor.py     # LSTM ensemble component (optional)
├── trade_manager.py      # Lot sizing, SL/TP, BE, trailing stop
├── executor.py           # Order placement + slippage handling
├── paper_trader.py       # Virtual trading simulation
├── kelly_sizer.py        # Kelly criterion position sizing
├── regime_detector.py    # Market regime classification
├── news_filter.py        # High-impact news event blocking
├── correlation_filter.py # Correlated pair duplicate filter
├── analytics.py          # Win rate, drawdown, R:R stats
├── performance_log.py    # CSV trade outcome tracking
├── dashboard.py          # Terminal live display
├── web_app.py            # Flask local web dashboard
├── siteground_api.py     # Pushes state to SiteGround PHP endpoint
├── telegram_alerts.py    # Telegram push notifications
├── watchdog.py           # Auto-restart + health monitoring
├── backtest.py           # Historical backtest runner
├── security.py           # Encrypted credential storage
├── deploy/               # PHP web dashboard (upload to SiteGround)
├── models/               # Trained model files (auto-created)
└── logs/                 # Trade + signal logs (auto-created)
```

---

## Requirements

- Python 3.10+
- MetaTrader 5 (desktop) with a Pepperstone Demo account
- Windows (MT5 Python API is Windows-only)

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For LSTM support (optional, needs ~2GB RAM):
```bash
pip install tensorflow>=2.15.0
```

### 2. Secure your credentials

```bash
python security.py --setup
```

This encrypts your MT5 login/password locally. Never put credentials in `config.py` directly.

### 3. Create required folders

```bash
mkdir models logs
```

### 4. Train the AI model

```bash
python main.py --train
```

Pulls 500 bars per symbol, trains XGBoost on ~3,000–10,000 samples, saves to `models/xgb_forex.pkl`.

### 5. Run in paper trading mode (default)

```bash
python main.py
```

`PAPER_TRADING = True` is the default in `config.py`. Test for at least 2–4 weeks before going live.

### 6. Run a backtest

```bash
python main.py --backtest
```

---

## Configuration

All settings live in `config.py`. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `PAPER_TRADING` | `True` | Set `False` only after demo success |
| `RISK_PERCENT` | `1.0` | % of account risked per trade |
| `MIN_WIN_PROBABILITY` | `0.65` | AI confidence threshold |
| `MAX_DAILY_DRAWDOWN` | `5.0` | Halt trading if daily loss exceeds this % |
| `USE_KELLY_SIZING` | `True` | Kelly criterion sizing vs flat risk |
| `USE_LSTM` | `True` | Include LSTM in ensemble |
| `USE_NEWS_FILTER` | `True` | Block trades during news events |
| `SKIP_NON_TRENDING_REGIMES` | `True` | Only trade trending markets |

---

## Dashboard Controls (terminal)

While the bot is running:

| Key | Action |
|-----|--------|
| `T` | Force immediate scan |
| `R` | Retrain AI model now |
| `Q` | Quit safely |

---

## Web Dashboard (SiteGround)

The `deploy/` folder contains a PHP dashboard your clients or team can view from any browser.

1. Upload `deploy/` contents to `public_html/fxpulse/` on SiteGround
2. Set `SITEGROUND_API_URL` and `SITEGROUND_API_KEY` in `config.py`
3. The bot pushes a state snapshot every 60 seconds

---

## Telegram Alerts

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `config.py`

---

## Symbols Traded

- **Majors:** EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD
- **Minors:** EURGBP, EURJPY, GBPJPY, AUDJPY, CADJPY, GBPCHF, EURAUD
- **Exotics:** USDTRY, USDZAR, USDMXN, USDSEK, USDNOK
- **Commodities:** XAUUSD, US500, NAS100, UK100

All use Pepperstone `.a` suffix (e.g. `EURUSD.a`).

---

## Risk Warning

This software is for educational and research purposes. Forex trading carries significant risk of loss. Always test thoroughly on a demo account before risking real capital. Past performance does not guarantee future results.

---

## License

MIT
